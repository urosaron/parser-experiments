**AI Pipeline: RAG and Parser Architecture**

Trans Realities Lab  ·  Holodeck Project  ·  March 2026

Author: Uroš Aron Čolović

**Contents**

	1.  Purpose and Scope	2

	What is the parser?	2

	What is a CDN?	2

	2.  Architecture Overview	2

	3.  The Two Lookup Problems	3

	3.1  Existing objects: the ID comes from the input	3

	3.2  New objects: the ID does not exist yet	4

	4.  How the RAG Works	5

	4.1  What gets indexed in the vector database	5

	4.2  Concrete example	5

	4.3  Similarity threshold	6

	5.  Parser Output Schema	6

	5.1  Spawn command (RAG lookup required)	6

	5.2  Edit command (no RAG lookup)	7

	5.3  Delete command (no RAG lookup)	7

	5.4  No command	7

	6.  Proposed Local Stack	7

	7.  Open Questions	8

	8.  Conclusion	8

# 1.  Purpose and Scope

This document clarifies the architecture of the AI pipeline for the Holodeck, specifically how the parser and the RAG (Retrieval-Augmented Generation) system interact. It covers what each component does, how data flows between them, and what the parser's input and output should look like in practice.

It does not cover ASR model benchmarking, fine-tuning methodology, or server infrastructure. Those are addressed separately in the project plan and devlog.

## What is the parser?

The parser is a Large Language Model (LLM), the same class of AI model that powers tools like ChatGPT. An LLM is used here because voice commands are inherently ambiguous. A user might say move that a bit to the left, bring it closer, or slide the oak table forward and all of these mean roughly the same thing. A traditional rule-based system cannot handle this variety reliably. An LLM can understand the intent behind natural language and translate it into a precise, structured instruction that the 3D scene can act on.

The parser receives a voice transcript and the current state of the scene, and outputs a JSON object describing exactly what action to perform on which object.

## What is a CDN?

CDN stands for Content Delivery Network. In simple terms it is a file hosting service optimised for fast delivery. Think of it as a large library of files sitting on a server that anyone can download from quickly via a URL.

In the Holodeck, the CDN is where all the 3D mesh files are stored. A mesh file is the actual 3D model that gets rendered in the scene, for example a chair, a table, or a lamp. When the scene needs to load a new object, it fetches the mesh file from the CDN using a URL such as:

https://cdn.holodeck.com/assets/furniture/wooden_chair_v2.glb

The CDN itself has no understanding of language or meaning. It simply stores files and hands them out when asked. The RAG system, described in section 4, is what bridges the gap between what a user says and which file URL to fetch.

# 2.  Architecture Overview

A voice command in the Holodeck passes through six stages before it results in an action in the 3D scene. The diagram below shows the full pipeline, with the components relevant to this document highlighted.

| **1  Voice**** input** User speaks to the Holodeck |
| --- |
| ▼ |
| **2  ASR**** (Whisper)** Audio → raw transcript text |
| ▼ |
| **3  Parser**** AI** Transcript + scene context → structured intent |
| ▼ |
| **4  CDN**** + RAG** asset_query → asset URL  (spawn commands only) |
| ▼ |
| **5  ****Colyseus**** Server** Validates command, syncs all clients |
| ▼ |
| **6  ****BabylonJS**** Scene** Executes action on the correct mesh |

The Parser AI and CDN + RAG boxes are the focus of this document. Everything before the parser (stages 1 and 2) and after it (stages 5 and 6) is either handled by existing infrastructure or outside the scope of the AI pipeline work.

The parser receives its input from the scene server, which sends a filtered list of nearby scene objects along with the audio transcript. The server owns the logic of which scene objects to include in that context. The parser does not need to reason about the full scene.

# 3.  The Two Lookup Problems

Not all commands need the same information to execute. There are two fundamentally different situations depending on whether the object the user refers to already exists in the scene or not.

| **Lookup 1: existing objects** Command type: edit, move, delete, rotate, scale, hide/show Object already exists in scene ID is already in the scene context from the server RAG not needed |  | **Lookup 2: new assets** Command type: spawn Asset does not exist in scene yet Parser outputs asset_query RAG resolves query to CDN URL |  | **Result** The final command always contains a resolved ID or URL No unresolved references ever leave the pipeline |
| --- | --- | --- | --- | --- |

## 3.1  Existing objects: the ID comes from the input

When a user says something like move the red chair to the left, the chair is already in the scene. The scene server, before contacting the parser, has already compiled a list of nearby objects and their server-assigned IDs. That list is sent to the parser as part of its input.

This means the parser does not need to look anything up. It reads the relevant ID directly from the input it was given and places it in the output command. No RAG, no CDN, no external call of any kind is needed.

| **Scene server input** Sends transcript + list of nearby objects with their IDs |
| --- |
| **v** |
| **Parser AI** Reads object ID from input, determines action |
| **v** |
| **Output command** { command: "edit", id: "server_abc123", changes: { ... } } |
| *No RAG or CDN involved. The ID was already in the input.* |

## 3.2  New objects: the ID does not exist yet

When a user says spawn a wooden chair, there is no chair in the scene yet and therefore no ID to read from the input. The parser has no way of knowing which 3D file to use or what ID the object will eventually have.

In this case the parser outputs a natural language description of what the user wants, called asset_query. The CDN + RAG service receives that description, finds the closest matching asset in its library, and returns the CDN file URL. The scene server then loads that file, creates a new mesh in the scene, and assigns it a fresh server-generated ID.

The CDN URL is a one-time fetch. Once the object is loaded into the scene it has its own ID, and from that point on all future commands referencing it follow the existing object path described above.

| **Scene server input** Sends transcript + nearby objects (no matching ID exists) |
| --- |
| **v** |
| **Parser AI** Recognises spawn intent, outputs asset_query: "wooden chair" |
| **v** |
| **CDN + RAG** Embeds query, finds closest asset, returns CDN file URL |
| **v** |
| **Scene server** Loads mesh file from URL, creates object, assigns new ID |
| **v** |
| **Object now in scene** All future commands reference it by its new server-assigned ID |
| *RAG and CDN involved only at spawn time. Never again for this object.* |

# 4.  How the RAG Works

RAG stands for Retrieval-Augmented Generation. In this context it is the semantic search layer that bridges natural language descriptions and CDN file URLs. It does not generate anything. It looks things up.

The RAG pipeline has two distinct phases:

| **Indexing phase (runs once)** 1.  Take each asset description 2.  Pass through embedding model to get a vector 3.  Store vector and metadata in ChromaDB |  | **Query phase (every spawn command)** 1.  Receive asset_query string from parser 2.  Embed with same model to get a vector 3.  Find closest match in ChromaDB 4.  Return asset URL |
| --- | --- | --- |

## 4.1  What gets indexed in the vector database

Each asset in the library has a name and a description. It is the description that gets indexed, not the name. The reason is that names are too short and literal to carry much semantic meaning. A name like "Wooden Chair" gives the embedding model very little to work with.

A description like "wooden chair four legs light oak finish" is what allows a query such as "oak seat" or "timber dining chair" to still return the correct result, even though those words do not appear in the name at all. The description captures material, shape, and style in a way that can be matched semantically.

In practice both name and description are stored in the database. The description is what gets turned into a vector and searched against. The name is metadata that comes back with the result so the system knows what it found.

## 4.2  Concrete example

The asset library contains an entry like this:

| **Field** | **Value** |
| --- | --- |
| name | Wooden Chair |
| description | wooden chair four legs light oak finish |
| url | https://cdn.holodeck.com/assets/furniture/wooden_chair_v2.glb |

When the user says "spawn a wooden chair near the window", the following happens:

- Parser outputs:  asset_query: "wooden chair near the window"

- The embedding model converts "wooden chair near the window" to a vector, e.g. [0.12, -0.84, 0.37, ...]

- ChromaDB finds the closest stored vector (the oak chair entry above)

- The CDN URL is returned and included in the final command

The key property of vector search is that it matches on meaning, not exact wording. A query of "oak seat" or "timber dining chair" would produce a similar vector and return the same result.

## 4.3  Similarity threshold

Vector search always returns the closest match, even if that match is poor. A similarity threshold filters out results below a minimum quality score. In practice:

| **Score** | **Meaning** | **Action** |
| --- | --- | --- |
| >= 0.85 | Strong match | Use the result |
| 0.75 to 0.84 | Probable match | Use with caution / log for review |
| < 0.75 | Weak or no match | Return error: asset not found |

The exact threshold will be determined empirically during Sprint 4 benchmarking against the real asset library.

# 5.  Parser Output Schema

The parser always outputs a single JSON object. The schema varies by command type. Below are the relevant cases with the asset_query field shown in context.

## 5.1  Spawn command (RAG lookup required)

The asset_query field is the parser's output to the CDN + RAG service. It is never sent to the scene server directly. By the time the command reaches the scene server, it has been replaced by a resolved asset_url.

Step 1: Parser outputs (asset_query not yet resolved):

  {

    "command":     "spawn",

    "asset_query": "wooden chair near the window",  // natural language, sent to RAG

    "name":        "Wooden Chair",

    "position":    { "x": 0, "y": 0, "z": -4 }

  }

Step 2: After RAG resolves the URL:

  {

    "command":   "spawn",

    "asset_url": "https://cdn.holodeck.com/assets/furniture/wooden_chair_v2.glb",

    "name":      "Wooden Chair",

    "position":  { "x": 0, "y": 0, "z": -4 }

  }

## 5.2  Edit command (no RAG lookup)

The object ID is resolved directly from the scene context the server already sent. No RAG step is involved. Only the fields that are changing are included inside changes.

  {

    "command": "edit",

    "id":      "server_abc123",   // server-assigned ID from scene context

    "changes": {

      "position": { "x": 5, "y": 0, "z": -3 }

    }

  }

## 5.3  Delete command (no RAG lookup)

  {

    "command":        "delete",

    "id":             "server_c991a",  // server-assigned ID from scene context

    "deleteChildren": false             // true removes all child objects too

  }

## 5.4  No command

When the transcript contains no actionable instruction, such as a question, filler speech, or general conversation.

  { "command": "none" }

# 6.  Proposed Local Stack

All components run locally on the lab workstation (Wilbur). No cloud services are required for development or testing.

| **Component** | **Role** |
| --- | --- |
| Ollama | Serves the parser LLM (Qwen, Mistral, etc.) locally |
| sentence-transformers | Converts text descriptions to vectors for the RAG |
| ChromaDB | Stores and queries vectors, runs in-process |

sentence-transformers and ChromaDB are both pip-installable and run in-process alongside the existing Ollama setup. They do not require a separate server or any additional infrastructure.

During development a small synthetic asset library will be used in place of real CDN assets. This allows the full RAG pipeline to be built and tested end-to-end without depending on production infrastructure or a finalised asset catalogue being ready.

| **Ollama**** vs sentence-transformers for embeddings** Ollama does support embeddings and would keep the stack simpler. The plan is to try it first. If the embedding quality or model selection turns out to be insufficient for reliable asset retrieval, sentence-transformers is the fallback. It has a wider selection of well-benchmarked embedding models and integrates natively with ChromaDB. |
| --- |

# 7.  Open Questions

The following items are not yet resolved and will affect Sprint 4 implementation. They are listed here so the relevant people are aware.

| **Question** | **Owner** |
| --- | --- |
| How many objects does the scene server filter before sending context to the parser? | Balsa + Zak |
| What are the real CDN base URLs for the asset library? | Zak |
| What is the correct similarity threshold for the asset library? | Uroš (benchmarking) |
| Will the asset library use real CDN hosting or local file paths for development? | Zak |

# 8.  Conclusion

This document was produced as a research output to clarify how the RAG and parser components fit together architecturally, ahead of the point where RAG work becomes active. The key takeaways are that the two lookup problems are fundamentally different and require different solutions, that the CDN URL is only ever needed at spawn time, and that the scene server handles object filtering before the parser is involved at all.

The open questions listed in section 7 will need to be resolved with the team before implementation begins. What comes next in the project will be determined in discussion with Zak.
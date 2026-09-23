# RAG design

## Source document types

The demo corpus contains Markdown operating procedures, equipment
troubleshooting guides, and safe-isolation instructions under
`rag/documents/`. The ingestion interface can be extended to PDF or HTML
extractors without changing retrieval.

## Ingestion flow and text extraction

`rag/ingestion/ingest.py` scans the configured directory for `.md` files,
reads UTF-8 text, parses the small YAML-like front matter, and creates
LangChain `Document` records. The Markdown heading is retained as the section
boundary and citation context. RAG runs
before the LangGraph answer loop, so the same user request supplies document
evidence alongside MCP evidence in the final grounded answer.

## Chunking strategy

Chunking is document-aware first: each H1-H3 section is isolated before
splitting. Long sections use `RecursiveCharacterTextSplitter` with an 800
character target and 120 character overlap. Each chunk also repeats the
document title and section name so a retrieved chunk remains self-contained.
This preserves procedure steps
better than splitting the whole corpus at arbitrary character offsets while
still bounding prompt size.

## Chunk metadata

Every chunk stores `source` (the file name), `source_id`, `title`, `type`,
`asset_id`, `site`, `revision`, `effective_date`, `section`, `chunk`, and
`document_type` metadata. These fields are used for citations, debugging, and
future source/type/asset filters.

## Embeddings, vector index, and hybrid search

The retrieval layer uses LangChain's FAISS vector store with OpenAI's
`text-embedding-3-small` through `OpenAIEmbeddings`. The embedding client is
cached once per process and the model can be changed with
`RAG_EMBEDDING_MODEL` without changing the index interface. Document and query
text are sent to the configured OpenAI API for embedding, so deployment must
approve that data flow.

Retrieval is hybrid: FAISS returns vector candidates, then lexical term
overlap is combined with the normalized vector score. Results are sorted by
the combined score. This helps exact equipment names and alarm IDs while
retaining fuzzy token similarity.

## Ranking, filters, and citations

The combined score is `lexical_term_count + 1 / (1 + faiss_distance)`.
The API applies `top_k` after ranking. Source, section, and chunk metadata are
returned with an excerpt and are cited as `[DOC:source]` by the answer prompt.
The current filter surface is the Markdown corpus directory; metadata filters
are available for future site, revision, or document-type constraints.

## Low-confidence handling

No matching chunks returns an empty source list. The answer prompt instructs
the LLM not to invent facts and to distinguish missing procedure evidence
from API evidence. A production threshold should be calibrated against a
labelled evaluation set before suppressing low-scoring results.

## Prompt-injection protections

Retrieved text is treated as untrusted evidence, not instructions. The system
prompt tells the LLM to follow application instructions over document text,
never execute document-supplied commands, and use MCP for operations. RAG has
no write tools or source-system credentials.

## Index refresh process

The compact implementation rebuilds the in-memory FAISS index on each
retrieval, so editing or adding a Markdown file is immediately visible and
there is no stale index artifact to manage. For a larger corpus, run ingestion
as a scheduled job, persist FAISS with an audited versioned directory, and
reload only after validating the source manifest.

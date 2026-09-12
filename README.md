# AI Research Paper Agent

A clean end-to-end research-paper assistant:

arXiv → AI filtering → PDF → text/section extraction → chunks → BGE embeddings → Supabase/pgvector → hybrid retrieval → cross-encoder reranking → Qwen → Telegram

## 1. Requirements

- Python 3.11+ recommended
- A Supabase project
- A Telegram bot token
- Qwen available through Ollama (recommended model: `qwen2.5:7b` or another Qwen model you have installed)
- Internet access for arXiv/PDF/model downloads

## 2. Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`.

Start Ollama and make sure your Qwen model is available:

```bash
ollama pull qwen2.5:7b
ollama serve
```

## 3. Database

Open Supabase SQL Editor and run:

```text
database/schema.sql
```

## 4. Test the pipeline

Run:

```bash
python -m backend.services.paper_pipeline
```

Then test retrieval:

```bash
python -m backend.services.vector_search
```

Then test RAG:

```bash
python -m backend.services.rag_service
```

## 5. Start Telegram bot

```bash
python -m backend.services.telegram_bot
```

## 6. Start the arXiv monitor

```bash
python -m backend.services.new_paper_detector
```

The monitor checks arXiv periodically and ingests relevant papers. Telegram users can ask arbitrary questions about a selected paper.

## Architecture

```text
                    arXiv
                      |
               Paper Retriever
                      |
             AI Relevance Filter
                      |
                    PDF
                      |
          +-----------+-----------+
          |                       |
     PDF Extraction         Paper Metadata
          |
   Structure-aware Chunks
          |
    BGE-small-en-v1.5
          |
     Supabase/pgvector
          |
     +----+----------------+
     |                     |
Vector Retrieval      Lexical Retrieval
     |                     |
     +---------+-----------+
               |
        Candidate Pool
               |
      Cross-Encoder Reranker
               |
           Top Chunks
               |
        Context Builder
               |
             Qwen
               |
        Grounded Answer
               |
           Telegram
```

## Important

This repository deliberately avoids paper-specific rules. Sections are metadata for context/source attribution, not hard-coded retrieval routes.

For production deployment, move secrets to environment variables and tighten Supabase RLS policies.

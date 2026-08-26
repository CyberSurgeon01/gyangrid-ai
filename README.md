# GyanGrid AI

**GyanGrid AI** is a full-stack, AI-powered research paper analysis platform built with **Streamlit**, designed to simplify how researchers, students, and academics interact with scholarly literature. Instead of manually reading hundreds of pages to extract key insights, GyanGrid AI enables users to upload research papers and instantly explore them through an intelligent Retrieval-Augmented Generation (RAG) assistant.

The platform combines **Google Gemini**, **FAISS vector search**, **OpenAlex**, **Semantic Scholar**, and **Supabase** to provide a comprehensive research workflow. Users can upload PDF or DOCX papers, ask context-aware questions, generate AI-powered summaries, identify research gaps and future work, compare multiple papers side-by-side, visualize citation relationships, discover related publications, listen to summaries using text-to-speech, and export results as PDF reports.

With secure authentication, persistent document history, semantic search, and an intuitive dashboard, GyanGrid AI transforms traditional literature review into a faster, more interactive, and AI-assisted research experience.


![GyanGrid AI Showcase](assets/gyangrid-showcase-fhd.gif)
## Features

- 🔐 **Flexible Authentication** — email/password login, Google OAuth, Gmail-based OTP email verification for sign-up, and a "Continue without login" guest mode. Accounts and data are stored in Supabase.
- 📤 **Paper Upload** — PDF/DOCX up to 20MB, up to 3 papers tracked at once
- 📊 **Dashboard** — document overview per paper: character count, chunk count, sections found, section-aware chunks, and reference count
- 💬 **RAG-Powered Q&A** — ask grounded questions and get answers sourced directly from the paper, via FAISS + Google Gemini
- ✨ **AI Analysis** — auto-generated paper summary, key topics, research gaps, and likely reviewer questions; results include novelty, research gap, future work, conclusion summary, and core technology tags. Citation support and an AI readiness score are on the roadmap.
- 🆚 **Compare** — side-by-side comparison of two papers across novelty, research gap, methodology, results, future work, and conclusion, with an AI verdict summary (similarity %, better novelty/methodology/results, future potential, overall winner)
- 🔗 **Related Papers Discovery** — surfaces relevant academic papers via OpenAlex and Semantic Scholar APIs
- 🕸️ **Citation Graph** — visualize citation relationships
- 🔊 **Text-to-Speech** — listen to paper summaries via gTTS
- 📄 **PDF Export** — export analysis and notes to PDF via LibreOffice
- 📜 **History** — revisit and reopen previously uploaded papers


![GyanGrid AI Demo](assets/gyangrid-demo.gif)

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend/App | Streamlit |
| Vector Search | FAISS |
| LLM / RAG | Google Gemini |
| Auth & DB | Supabase |
| Paper Metadata | OpenAlex API, Semantic Scholar API |
| Text-to-Speech | gTTS |
| PDF Export | LibreOffice |

## Live Demo

Deployed on Streamlit Community Cloud — [add your live link here]

## Getting Started

### Prerequisites

- Python 3.9+
- A Supabase project (URL + API key)
- A Google Gemini API key

### Installation

```bash
git clone https://github.com/<your-username>/gyangrid-ai.git
cd gyangrid-ai
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
GEMINI_API_KEY=your_gemini_api_key
```

### Run Locally

```bash
streamlit run app.py
```

## Roadmap

- [ ] Citation Support (verified in-text citations cross-checked against source references)
- [ ] AI Readiness Score (how well-structured a paper is for automated analysis)
- [ ] Multi-language paper summarization

## License

This project is licensed under the [MIT License](LICENSE).

## Author

**Rahul Chandra Shil**
[https://www.linkedin.com/in/rahul-chandra-shil/](#) · [https://github.com/CyberSurgeon01](#)
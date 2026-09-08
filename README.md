# DocuChat AI 🤖

**Intelligent Document Q&A System with Real-Time AI Responses**

Upload documents (PDF, TXT, DOCX) and ask questions. Get accurate, AI-powered answers with source citations in real-time.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- OpenAI API Key

### Installation & Running

**1. Backend Setup**
```bash
cd backend
pip install -r requirements.txt
echo "OPENAI_API_KEY=your-key-here" > .env
uvicorn app.main:app --reload
```

**2. Frontend Setup** (New Terminal)
```bash
cd frontend
npm install
npm run dev
```

**3. Access Application**
Open browser → **http://localhost:5173**

---

## 📖 Documentation

- **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** - One-page overview (for quick review)
- **[PROJECT_REPORT.md](PROJECT_REPORT.md)** - Comprehensive guide (for detailed understanding)
- **[CLAUDE.md](CLAUDE.md)** - Technical implementation details (for developers)
- **[LEARNING.md](LEARNING.md)** - RAG concepts explained (for learning)

---

## ✨ Key Features

- 🤖 **AI-Powered**: OpenAI GPT-3.5 for intelligent answers
- ⚡ **Real-Time Streaming**: Watch answers appear word-by-word
- 📊 **Token Tracking**: Monitor API usage and costs
- 🔒 **Secure**: 3-layer prompt injection defense
- 🎨 **Modern UI**: Clean, professional design
- 📄 **Multi-Format**: PDF, TXT, DOCX support

---

## 🎯 How It Works

1. **Upload** a document (PDF, TXT, or DOCX)
2. **Ask** a question in natural language
3. **Get** AI-powered answer with source citations
4. **Track** token usage for each interaction

---

## 🛠️ Technology Stack

**Frontend**: React, Vite, Tailwind CSS v4, Vercel AI SDK v4
**Backend**: Python FastAPI, OpenAI API, FAISS, LangChain
**Architecture**: RAG (Retrieval-Augmented Generation)

---

## 📸 Screenshots

### Main Interface
- **Left Sidebar**: Document management, session stats
- **Center Area**: Chat interface with streaming responses
- **Bottom Input**: Question input with send button

### Features Shown
- Real-time streaming responses
- Token usage tracking (prompt • completion • total)
- Source citations for each answer
- Modern, minimalistic design

---

## 🎓 What This Project Demonstrates

- Full-stack development (React + Python)
- AI integration with OpenAI API
- Vector databases with FAISS
- Real-time streaming (Server-Sent Events)
- Security engineering (multi-layer defense)
- Modern UI/UX design
- RAG architecture implementation

---

## 📊 Project Stats

- **Code**: ~1,300 lines (500 frontend + 800 backend)
- **Components**: 15+ reusable components
- **API Endpoints**: 5 RESTful routes
- **Response Time**: 2-5 seconds
- **Max File Size**: 10 MB

---

## 🔐 Security Features

- **Layer 1**: Input sanitization
- **Layer 2**: Prompt injection detection
- **Layer 3**: System prompt hardening
- **Rate Limiting**: 20 requests/min per IP
- **No Persistent Storage**: Session-based only

---

## 💡 Example Questions

- "What is the main topic of this document?"
- "Summarize the key points"
- "When was [event] mentioned?"
- "List all names/dates/locations mentioned"
- "Can you find any relation between [A] and [B]?"

---

## 📁 Project Structure

```
Document Q&A bot/
├── backend/              # Python FastAPI server
│   ├── app/
│   │   ├── routers/      # API endpoints
│   │   ├── services/     # Business logic
│   │   └── store/        # Vector database
│   └── requirements.txt
├── frontend/             # React application
│   ├── src/
│   │   ├── components/   # UI components
│   │   └── hooks/        # React hooks
│   └── package.json
├── README.md            # This file
├── EXECUTIVE_SUMMARY.md # One-page overview
├── PROJECT_REPORT.md    # Detailed documentation
├── CLAUDE.md           # Technical guide
└── LEARNING.md         # Educational guide
```

---

## 🚧 Future Enhancements

- Multi-document comparison
- Conversation history
- Export answers (PDF/TXT)
- Voice input
- GPT-4 support
- Dark mode
- Collaborative features

---

## 📝 Notes

- **Similarity Threshold**: 1.8 (tuned through testing)
- **Temperature**: 0.3 (balanced for accuracy)
- **Top-K Results**: 8 chunks retrieved per query
- **Chunk Size**: 1000 characters with 200 overlap

These values were carefully tuned. Modifying them may affect performance.

---

## 🏆 Status

✅ Complete & Production-Ready
✅ Modern Tech Stack (2026)
✅ Security Hardened
✅ Professionally Designed
✅ Fully Documented

---

## 📞 Getting Help

For detailed information:
- **Quick Overview**: See [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)
- **Full Details**: See [PROJECT_REPORT.md](PROJECT_REPORT.md)
- **Technical Info**: See [CLAUDE.md](CLAUDE.md)
- **Learn RAG**: See [LEARNING.md](LEARNING.md)

---

**Built with ❤️ using OpenAI, React, FastAPI, and modern AI technologies**

*Version 1.0.0 | February 2026*

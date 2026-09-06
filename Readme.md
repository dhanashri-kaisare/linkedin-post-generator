# 🚀 LinkedIn Post Generator

An AI-powered LinkedIn post generator built with **LangGraph**.

The application generates LinkedIn posts, reviews them using a separate AI reviewer, and automatically improves rejected drafts through an iterative self-review loop.

## ✨ Features

* 🤖 AI-powered LinkedIn post generation
* 🔄 Iterative self-review and improvement loop
* 🧠 LangGraph state-based workflow
* 🔀 Conditional routing based on review results
* 🔍 Tavily web search for current information when needed
* 👀 Separate AI reviewer for quality evaluation
* 🔢 Maximum review-attempt control
* 📥 Download generated posts as `.txt`
* 🌐 Streamlit web interface

## 🛠️ Tech Stack

* Python
* LangGraph
* LangChain
* Groq
* Google Gemini
* Tavily
* Streamlit
* python-dotenv

## 🔄 How It Works

```text
User enters a topic
        ↓
     Writer
        ↓
  Web Search? ─── Yes ──→ Tavily
        │                    │
        └────── No ←─────────┘
        ↓
   Draft Generated
        ↓
     Reviewer
        ↓
   ┌────┴─────┐
   │          │
Approved    Rejected
   │          │
   ↓          ↓
  END      Writer
              │
              ↓
        Improved Draft
              │
              ↓
           Reviewer
```

If the reviewer rejects a draft, the feedback is passed back to the writer so that the next draft can address the identified issues. The workflow stops when the post is approved or the maximum number of review attempts is reached.

## 📁 Project Structure

```text
linkedin-post-generator/
│
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
│
└── workflow/
    ├── iterative_workflow.py
    └── streamlit_app.py
```

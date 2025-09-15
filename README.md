---
title: Heartfulness Article Viewer
emoji: 📖
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: 1.49.1
app_file: pages/byte_extractor_app.py
pinned: false
license: mit
---

# Heartfulness Article Viewer

A Streamlit application for viewing and managing extracted articles from Heartfulness Magazine with AI-powered content summaries and review capabilities.

## Features

- 📂 **View Extracted Articles**: Browse articles from MongoDB with advanced filtering
- 🔍 **Smart Filtering**: Filter by year, summary status, and PDF edition
- ✅ **Review System**: Accept/reject content summaries with confirmation dialogs
- 📊 **Pagination**: Efficient handling of large article collections
- 🤖 **AI Integration**: Display LLM review results when available

## Usage

1. Select filters from the sidebar (Year, Summary Status, PDF Edition)
2. Browse through paginated articles
3. Review content summaries and accept/reject them
4. View detailed article content and AI review results

## Technical Details

- **Frontend**: Streamlit
- **Database**: MongoDB
- **Logging**: Comprehensive logging system
- **Security**: Environment variables for sensitive data

## Environment Variables

The app requires the following environment variables to be set in Hugging Face Spaces:

- `MONGODB_URL`: MongoDB connection string

## License

MIT License

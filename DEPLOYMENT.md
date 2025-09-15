# Hugging Face Spaces Deployment Guide

This guide will help you deploy the Heartfulness Article Viewer app on Hugging Face Spaces.

## Prerequisites

1. A Hugging Face account (you already have one: https://huggingface.co/imrajeshkr)
2. A MongoDB Atlas cluster or MongoDB instance
3. Git installed on your local machine

## Step 1: Create a New Space

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces)
2. Click "Create new Space"
3. Fill in the details:
   - **Space name**: `heartfulness-article-viewer`
   - **License**: MIT
   - **SDK**: Docker
   - **Hardware**: CPU Basic (free tier)
   - **Visibility**: Public

## Step 2: Set Up Environment Variables

1. In your Space settings, go to "Variables and secrets"
2. Add the following environment variable:
   - **Name**: `MONGODB_URL`
   - **Value**: Your MongoDB connection string (keep this secret!)

## Step 3: Upload Your Code

### Option A: Using Git (Recommended)

1. Initialize a git repository in your project folder:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. Add the Hugging Face Space as a remote:
   ```bash
   git remote add origin https://huggingface.co/spaces/imrajeshkr/heartfulness-article-viewer
   ```

3. Push your code:
   ```bash
   git push -u origin main
   ```

### Option B: Using the Web Interface

1. Upload all files through the Hugging Face Spaces web interface
2. Make sure to upload all files in the correct structure

## Step 4: Verify Deployment

1. Your app will be available at: `https://huggingface.co/spaces/imrajeshkr/heartfulness-article-viewer`
2. Check the logs to ensure everything is working correctly
3. Test the app functionality

## Docker-Specific Notes

### Build Process
- Hugging Face will automatically build your Docker image
- The build process may take 5-10 minutes
- Check the "Logs" tab for build progress

### Port Configuration
- The app runs on port 8501 inside the container
- Hugging Face automatically maps this to the public URL
- Health checks ensure the app is running properly

### Environment Variables
- All environment variables are available inside the container
- MongoDB connection will work seamlessly
- Logs are written to the `/app/logs` directory

## Security Notes

- ✅ MongoDB URL is stored as a secret environment variable
- ✅ No sensitive data is committed to the repository
- ✅ The app uses proper error handling for missing environment variables
- ✅ Logs don't expose sensitive information

## File Structure for Deployment

```
heartfulness-article-viewer/
├── README.md                 # Space description
├── requirements.txt          # Python dependencies
├── packages.txt             # System dependencies (empty)
├── config.py               # Configuration management
├── pages/
│   └── byte_extractor_app.py  # Main Streamlit app
├── modules/
│   ├── __init__.py
│   ├── byte_extractor_service.py
│   └── logger_config.py
└── .gitignore              # Git ignore rules
```

## Troubleshooting

### Common Issues:

1. **MongoDB Connection Failed**
   - Check if your MongoDB URL is correct
   - Ensure your MongoDB instance allows connections from Hugging Face IPs
   - Verify the environment variable is set correctly

2. **Import Errors**
   - Make sure all files are uploaded in the correct structure
   - Check that all dependencies are in requirements.txt

3. **App Not Loading**
   - Check the Space logs for error messages
   - Verify the app file path in README.md

## Monitoring

- Check the Space logs regularly
- Monitor MongoDB connection usage
- Set up alerts for any errors

## Updates

To update your deployed app:

1. Make changes locally
2. Commit and push to the Space:
   ```bash
   git add .
   git commit -m "Update description"
   git push
   ```

The Space will automatically rebuild with your changes.

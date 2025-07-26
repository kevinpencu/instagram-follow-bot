# Instagram Automation System

A full-stack Instagram automation system with Python Flask backend and React frontend.

## Quick Setup

### Python Server

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Airtable API credentials and AdsPower settings
   ```

3. **Start the server**
   ```bash
   python src/main.py
   ```
   Server runs on `http://localhost:5000`

### React App

1. **Navigate to React directory**
   ```bash
   cd react
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```
   App runs on `http://localhost:5173`

## API Endpoints

- `GET /profiles` - List all profiles
- `POST /start-all` - Start automation for all profiles  
- `POST /start-selected` - Start automation for selected profiles
- `GET /status` - Get current automation status

## Production Build

### React App
```bash
cd react
npm run build
npm run start
```

### Python Server
Configure production environment variables and run:
```bash
python src/main.py
```
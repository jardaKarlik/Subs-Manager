# 📧 Email Configuration Guide for Subscription Manager

## 🎯 Your Configuration: Gmail + Outlook + IMAP

Based on your setup, you need to configure:
1. **Gmail Account** (via Composio API)
2. **Outlook Account** (via IMAP)
3. **Third Email Account** (via IMAP)

## 📋 Step-by-Step Setup Instructions

### Step 1: Composio API Setup (for Gmail)

#### 1.1 Create Composio Account
1. Go to [https://app.composio.dev](https://app.composio.dev)
2. Sign up for a free account
3. Verify your email address

#### 1.2 Get API Key
1. After login, go to **Settings** → **API Keys**
2. Click **"Generate New API Key"**
3. Copy the API key (starts with `comp_`)
4. Save it securely - you'll need it for the `.env` file

#### 1.3 Connect Gmail Account
1. In Composio dashboard, go to **Integrations**
2. Find **Gmail** and click **"Connect"**
3. Follow OAuth flow to authorize your Gmail account
4. Note down your Gmail address for the `.env` file

### Step 2: Outlook IMAP Setup

#### 2.1 Enable IMAP in Outlook
1. Go to [https://outlook.live.com](https://outlook.live.com)
2. Sign in to your Outlook account
3. Go to **Settings** (gear icon) → **View all Outlook settings**
4. Navigate to **Mail** → **Sync email**
5. Under **IMAP**, make sure it's **enabled**

#### 2.2 Create App Password
1. Go to [https://account.microsoft.com/security](https://account.microsoft.com/security)
2. Sign in with your Outlook account
3. Go to **Security** → **Advanced security options**
4. Under **App passwords**, click **"Create a new app password"**
5. Choose **"Mail"** as the app type
6. Copy the generated password (16 characters)
7. Save this password - you'll need it for IMAP authentication

### Step 3: Third Email Account IMAP Setup

#### For Yahoo Mail:
- **IMAP Server**: `imap.mail.yahoo.com`
- **Port**: `993`
- **Security**: SSL/TLS
- **App Password Required**: Yes
  1. Go to Yahoo Account Security
  2. Generate app password for "Mail"

#### For Custom Domain/Other Providers:
- Contact your email provider for IMAP settings
- Common settings:
  - **Port**: Usually 993 (SSL) or 143 (STARTTLS)
  - **Security**: SSL/TLS recommended

### Step 4: Update .env File

Once you have all the credentials, update your `.env` file:

```bash
# Composio API Configuration
COMPOSIO_API_KEY=comp_your_api_key_here

# Gmail Configuration (via Composio)
GMAIL_USER_1=your_gmail@gmail.com
GMAIL_USER_2=  # Leave empty if only using one Gmail

# Outlook IMAP Configuration
IMAP_SERVER=outlook.office365.com
IMAP_PORT=993
IMAP_USER=your_outlook@outlook.com
IMAP_PASSWORD=your_16_char_app_password

# Third Email IMAP Configuration (if different from Outlook)
# IMAP_SERVER_2=imap.mail.yahoo.com  # Uncomment and modify if needed
# IMAP_PORT_2=993
# IMAP_USER_2=your_third@email.com
# IMAP_PASSWORD_2=your_app_password

# Database Configuration
DATABASE_NAME=subscriptions.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_PORT=3000
```

## 🔧 IMAP Server Settings Reference

### Outlook/Hotmail
- **Server**: `outlook.office365.com`
- **Port**: `993`
- **Security**: SSL/TLS

### Yahoo Mail
- **Server**: `imap.mail.yahoo.com`
- **Port**: `993`
- **Security**: SSL/TLS

### Gmail (if using IMAP instead of Composio)
- **Server**: `imap.gmail.com`
- **Port**: `993`
- **Security**: SSL/TLS

### Common Corporate/Custom Domains
- **Port**: Usually `993` (SSL) or `143` (STARTTLS)
- **Server**: Usually `mail.yourdomain.com` or `imap.yourdomain.com`

## ⚠️ Security Notes

### App Passwords vs Regular Passwords
- **Never use your regular email password** for IMAP
- Always create **app-specific passwords**
- App passwords are more secure and can be revoked individually

### Two-Factor Authentication
- Keep 2FA enabled on all email accounts
- App passwords work even with 2FA enabled
- This is the recommended secure setup

## 🧪 Testing Your Configuration

After updating the `.env` file:

1. **Test the API**:
   ```bash
   python test_api.py
   ```

2. **Check email parsing**:
   ```bash
   # The test will show if emails are being fetched successfully
   # Look for "Processed X emails" in the output
   ```

3. **Verify in browser**:
   - Open `http://localhost:8000/docs`
   - Test the `/api/parse-emails` endpoint

## 🚨 Troubleshooting

### Common Issues:

#### "Authentication failed"
- Double-check app passwords
- Ensure IMAP is enabled
- Verify server settings

#### "Connection timeout"
- Check firewall settings
- Verify IMAP server and port
- Try different security settings

#### "Composio API error"
- Verify API key is correct
- Check if Gmail account is properly connected
- Ensure API key has necessary permissions

## 📞 Need Help?

If you encounter issues:
1. Check the error messages in the terminal
2. Verify all credentials are correct
3. Test one email account at a time
4. Check your email provider's documentation

---

**Next Steps**: Once you have all the credentials, I'll help you update the `.env` file and test the real email integration!
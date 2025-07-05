# FormIQ iOS Local Testing Guide

This guide covers everything needed to test the FormIQ application on iOS locally using Xcode and iOS Simulator.

## 📋 Prerequisites

### Required Software
- **macOS** (required for iOS development)
- **Xcode 14+** (latest version recommended)
- **Node.js 18+**
- **iOS Simulator** (included with Xcode)
- **CocoaPods** (for iOS dependency management)

### Install Prerequisites

```bash
# Install Xcode from App Store (or Xcode Command Line Tools)
xcode-select --install

# Install CocoaPods
sudo gem install cocoapods

# Verify installations
xcode-select -p
pod --version
node --version
npm --version
```

## 🚀 Step-by-Step iOS Setup

### Step 1: Get Your Local IP Address

```bash
# Find your local IP address
ipconfig getifaddr en0
# Example output: 192.168.1.151
```

**Important:** Note this IP address - you'll need it for backend configuration.

### Step 2: Configure Backend for Mobile Access

Update your backend to accept connections from your mobile device:

```bash
cd backend

# Create/update .env with your local IP
echo "CORS_ORIGINS=http://localhost:3000,http://192.168.1.151:3000" >> .env
echo "FRONTEND_URL=http://192.168.1.151:3000" >> .env
```

**Start backend with network access:**

```bash
# Start backend on all interfaces (accessible from mobile)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Configure Frontend for Mobile Development

Update the frontend environment:

```bash
cd frontend

# Create development environment file
cat > .env.local << EOF
REACT_APP_API_URL=http://192.168.1.151:8000
REACT_APP_ENVIRONMENT=development
EOF
```

### Step 4: Update Capacitor Configuration

The `capacitor.config.json` has been updated to allow local network access. Verify it includes:

```json
{
  "server": {
    "allowNavigation": [
      "http://localhost:3000",
      "http://localhost:8000", 
      "http://192.168.1.*:3000",
      "http://192.168.1.*:8000"
    ],
    "cleartext": true
  }
}
```

### Step 5: Build and Sync iOS App

```bash
cd frontend

# Install dependencies
npm install

# Build the React app
npm run build

# Sync with Capacitor (this copies build to iOS)
npx cap sync ios

# Open in Xcode (optional - for advanced debugging)
npx cap open ios
```

### Step 6: Install iOS Dependencies

```bash
cd ios/App

# Install CocoaPods dependencies
pod install
```

### Step 7: Run on iOS Simulator

```bash
cd frontend

# Option 1: Run directly from command line
npx cap run ios

# Option 2: Run with specific simulator
npx cap run ios --target="iPhone 15"

# Option 3: Run and rebuild automatically
npm run cap:ios
```

### Step 8: Alternative - Open in Xcode

If you prefer using Xcode directly:

```bash
cd frontend
npx cap open ios
```

Then in Xcode:
1. Select a simulator (iPhone 15, iPad, etc.)
2. Click the "Play" button to build and run
3. Wait for the app to launch in simulator

## 🔧 Configuration Details

### Backend Network Configuration

**Update CORS settings in `backend/app/core/config.py`:**

```python
# Add your local IP to CORS origins
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://192.168.1.151:3000",  # Your local IP
    "http://localhost:8000",
    "http://192.168.1.151:8000",  # Your local IP
]
```

### Frontend API Configuration

**Update `frontend/src/services/apiService.ts` if needed:**

```typescript
const BASE_URL = process.env.REACT_APP_API_URL || 'http://192.168.1.151:8000';
```

### iOS App Configuration

**Key settings in `ios/App/App/Info.plist`:**

```xml
<!-- Allow HTTP connections for development -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>

<!-- Camera permissions -->
<key>NSCameraUsageDescription</key>
<string>FormIQ needs camera access to analyze your workout form</string>

<!-- Photo library permissions -->
<key>NSPhotoLibraryUsageDescription</key>
<string>FormIQ needs photo access to select workout videos</string>
```

## 📱 Testing the Authentication Flow on iOS

### Test Checklist

#### 1. **App Launch**
- [ ] App launches without errors
- [ ] FormIQ splash screen appears
- [ ] Redirects to sign-in page

#### 2. **User Registration**
- [ ] Can access registration form
- [ ] Form validation works
- [ ] Can submit registration
- [ ] Redirects to onboarding (new users)

#### 3. **User Login**
- [ ] Can access login form
- [ ] Form validation works
- [ ] Can submit login
- [ ] Redirects based on onboarding status

#### 4. **Onboarding Flow**
- [ ] Onboarding screens display correctly
- [ ] Can navigate between steps
- [ ] Can complete onboarding
- [ ] Redirects to dashboard after completion

#### 5. **Dashboard Access**
- [ ] Dashboard loads correctly
- [ ] Navigation works
- [ ] User can logout

#### 6. **Password Reset**
- [ ] Can access password reset
- [ ] Can submit email for reset
- [ ] Shows appropriate feedback

#### 7. **Social Authentication** (if configured)
- [ ] Google/Apple buttons appear
- [ ] OAuth flow initiates
- [ ] Handles callback correctly

### Test Script for iOS

Create a test checklist as you go through the app:

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: iOS App
cd frontend
npm run cap:ios

# Terminal 3: Check logs
cd frontend
npx cap run ios --verbose
```

## 🐛 Troubleshooting Common Issues

### Issue 1: App Won't Connect to Backend

**Symptoms:** Network errors, can't register/login

**Solutions:**
1. Check your IP address: `ipconfig getifaddr en0`
2. Update `.env.local` with correct IP
3. Ensure backend is running on `0.0.0.0:8000`
4. Check firewall settings

```bash
# Test backend accessibility from iOS
# In iOS Safari, visit: http://YOUR_IP:8000/docs
```

### Issue 2: Build Failures

**Symptoms:** Xcode build errors, pod install failures

**Solutions:**
```bash
# Clean and rebuild
cd frontend
rm -rf ios/App/Pods
rm ios/App/Podfile.lock
cd ios/App && pod install
npx cap sync ios
```

### Issue 3: Permissions Issues

**Symptoms:** Camera/photos don't work

**Solutions:**
1. Check `Info.plist` permissions
2. Reset iOS Simulator: Device > Erase All Content and Settings
3. Reinstall app

### Issue 4: Hot Reload Not Working

**Solutions:**
```bash
# Use live reload during development
cd frontend
npx cap run ios --livereload --external

# Or serve with external access
npm start -- --host 0.0.0.0
```

### Issue 5: CORS Errors

**Symptoms:** Authentication API calls fail

**Solutions:**
1. Add your IP to CORS origins in backend
2. Restart backend after config changes
3. Check browser dev tools in iOS Safari

## 🔍 Debugging Tools

### iOS Safari Web Inspector

1. Enable in iOS Simulator: Settings > Safari > Advanced > Web Inspector
2. Open Safari on Mac: Develop > Simulator > FormIQ
3. Use console to debug JavaScript errors

### Xcode Console

1. Open Xcode
2. Window > Devices and Simulators
3. Select your simulator
4. View device logs

### Capacitor Logs

```bash
# View detailed Capacitor logs
npx cap run ios --verbose

# View live logs
npx cap run ios --livereload --consolelogs
```

## 🚀 Development Workflow

### Recommended Development Flow

1. **Start Backend:**
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start Frontend with Live Reload:**
   ```bash
   cd frontend
   npx cap run ios --livereload --external
   ```

3. **Make Changes:**
   - Edit React components
   - Changes automatically sync to iOS
   - Authentication flow updates in real-time

4. **Test Features:**
   - Registration → Onboarding → Dashboard
   - Login → Dashboard (existing users)
   - Password reset flow
   - Form analysis (video upload)

## 📊 Performance Considerations

### Optimizations for iOS Testing

```bash
# Build optimized version for testing
npm run build
npx cap sync ios
npx cap run ios --prod
```

### Memory Management

- Use iOS Simulator with sufficient RAM
- Close other applications during testing
- Reset simulator if memory issues occur

## 🔐 Security for Local Testing

### Network Security

- Only use HTTP for local testing
- Production builds must use HTTPS
- Don't commit local IP addresses to git

### Test Data

- Use test email addresses
- Don't use real OAuth credentials in development
- Clear test data between sessions

## 📱 Device Testing (Optional)

### Test on Physical iPhone

1. **Enable Developer Mode:**
   - Connect iPhone to Mac
   - Trust computer
   - Enable Developer Mode in Settings

2. **Run on Device:**
   ```bash
   npx cap run ios --target="Your iPhone Name"
   ```

3. **Network Configuration:**
   - Ensure iPhone and Mac on same WiFi
   - Backend must be accessible from iPhone's IP

## 🎯 Next Steps After iOS Testing

1. **Fix Issues Found:**
   - Authentication flow problems
   - UI/UX issues on mobile
   - Network connectivity issues

2. **Performance Testing:**
   - App startup time
   - Authentication speed
   - Form analysis performance

3. **Feature Testing:**
   - Camera integration
   - Video upload/analysis
   - Offline functionality

4. **Production Preparation:**
   - App Store preparation
   - HTTPS configuration
   - Production build optimization

---

## ✅ Quick Start Commands

```bash
# 1. Get your IP
ipconfig getifaddr en0

# 2. Start backend (replace IP)
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Update frontend config
cd frontend
echo "REACT_APP_API_URL=http://YOUR_IP:8000" > .env.local

# 4. Build and run iOS
npm run build && npx cap sync ios && npx cap run ios
```

**🎉 Your FormIQ app should now be running on iOS Simulator!**

Test the complete authentication flow:
1. Register new user → Onboarding → Dashboard  
2. Login existing user → Dashboard
3. Password reset functionality
4. App navigation and UI responsiveness
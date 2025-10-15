# Quick Deploy Checklist

## 🎯 Split Deployment: Vercel/Cloudflare + Render

### 1. Backend (Render) - 5 minutes

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push
   ```

2. **Deploy on Render**
   - Visit: https://dashboard.render.com
   - New → Web Service
   - Connect repository
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd api && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add env variables (see `.env.example`)
   - Deploy!

3. **Save Backend URL**
   ```
   https://your-backend.onrender.com
   ```

---

### 2. Frontend (Vercel) - 3 minutes

1. **Deploy on Vercel**
   - Visit: https://vercel.com
   - New Project → Import repository
   - **Framework**: Vite (auto-detected)
   - **Environment Variable**:
     ```
     VITE_API_URL=https://your-backend.onrender.com
     ```
   - Deploy!

2. **Update Backend CORS**
   - Go to Render → Environment Variables
   - Add: `FRONTEND_URL=https://your-app.vercel.app`
   - Redeploy backend

---

### 2. Frontend (Cloudflare) - Alternative

1. **Deploy on Cloudflare Pages**
   - Visit: https://dash.cloudflare.com
   - Workers & Pages → Create → Connect Git
   - **Build Command**: `npm run build`
   - **Output**: `dist/public`
   - **Environment Variable**:
     ```
     VITE_API_URL=https://your-backend.onrender.com
     ```
   - Deploy!

2. **Update Backend CORS**
   - Go to Render → Environment Variables
   - Add: `FRONTEND_URL=https://your-app.pages.dev`
   - Redeploy backend

---

### 3. Email Setup (Resend)

1. **Verify Domain**
   - Visit: https://resend.com
   - Add your domain
   - Add DNS records (SPF, DKIM)

2. **Add to Render**
   ```
   RESEND_API_KEY=re_xxxxx
   FROM_EMAIL=noreply@yourdomain.com
   ```

---

### 4. Test Everything ✅

- [ ] Backend health: `https://your-backend.onrender.com/`
- [ ] Frontend loads: `https://your-app.vercel.app`
- [ ] User registration works
- [ ] Email verification works
- [ ] Problem solving works
- [ ] No CORS errors in browser console

---

## 📝 Required Environment Variables

### Backend (Render)
```bash
DATABASE_URL=<from_render_postgres>
FRONTEND_URL=https://your-app.vercel.app
RESEND_API_KEY=re_xxxxx
FROM_EMAIL=noreply@yourdomain.com
GEMINI_API_KEY=xxxxx
SECRET_KEY=random_string
ADMIN_SECRET_KEY=random_string
```

### Frontend (Vercel/Cloudflare)
```bash
VITE_API_URL=https://your-backend.onrender.com
```

---

## 🚨 Common Issues

**CORS Error?**
→ Check `FRONTEND_URL` is set in Render
→ Must include `https://`

**Backend Slow?**
→ Free tier spins down after 15 min
→ Upgrade to keep-alive

**Email Not Sending?**
→ Verify domain in Resend
→ Check spam folder

---

## 📚 Full Guide
See `DEPLOYMENT_GUIDE.md` for detailed instructions

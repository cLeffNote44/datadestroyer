# Deploy to Vercel

Quick guide to deploy the Data Destroyer landing page to Vercel.

## Prerequisites

- Vercel account (free): https://vercel.com/signup
- Git repository with the landing page

## Method 1: Deploy via Vercel Dashboard (Easiest)

### Step 1: Push to GitHub

Make sure your landing page is pushed to GitHub:

```bash
cd /path/to/datadestroyer
git add landing-page/
git commit -m "Add landing page"
git push origin main
```

### Step 2: Import to Vercel

1. Go to https://vercel.com/new
2. Click **"Import Git Repository"**
3. Select your `datadestroyer` repository
4. **Important Settings:**
   - **Root Directory**: `landing-page`
   - **Framework Preset**: Other
   - **Build Command**: (leave empty)
   - **Output Directory**: (leave empty - it's a static site)

5. Click **"Deploy"**

### Step 3: Done! 🎉

Your site will be live at: `https://your-project-name.vercel.app`

You'll also get:
- Automatic HTTPS
- Global CDN
- Instant deployments on git push
- Preview deployments for PRs

## Method 2: Deploy via Vercel CLI

### Install Vercel CLI

```bash
npm install -g vercel
```

### Deploy

```bash
cd datadestroyer/landing-page

# Login to Vercel
vercel login

# Deploy
vercel

# Follow the prompts:
# - Set up and deploy? Yes
# - Which scope? (your account)
# - Link to existing project? No
# - Project name? data-destroyer
# - Directory? ./
# - Override settings? No

# Deploy to production
vercel --prod
```

## Custom Domain

### Add Your Domain

1. Go to your project on Vercel
2. **Settings** → **Domains**
3. Add your domain: `datadestroyer.com`
4. Follow DNS instructions

**DNS Records to Add:**

For `datadestroyer.com`:
```
Type: A
Name: @
Value: 76.76.21.21
```

For `www.datadestroyer.com`:
```
Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

Vercel will automatically provision SSL certificates!

## Continuous Deployment

Once connected, Vercel automatically:
- ✅ Deploys on every push to `main`
- ✅ Creates preview URLs for pull requests
- ✅ Runs on a global CDN
- ✅ Provides analytics

## Environment Variables (If Needed)

If you add a backend API later:

1. **Settings** → **Environment Variables**
2. Add variables:
   - `API_URL`
   - `ANALYTICS_ID`
   - etc.

Access in JavaScript:
```javascript
const apiUrl = process.env.API_URL || 'https://api.datadestroyer.com';
```

## Performance Optimization

Vercel automatically:
- ✅ Compresses assets
- ✅ Serves via global CDN
- ✅ Enables HTTP/2
- ✅ Optimizes images (with Vercel Image Optimization)

### Add Image Optimization (Optional)

If you add screenshots, use Vercel's Image component:

```html
<!-- Before -->
<img src="assets/images/dashboard.png" alt="Dashboard">

<!-- After (requires Next.js or image optimization) -->
<!-- Or just use optimized images - see SCREENSHOT_GUIDE.md -->
```

## Vercel Analytics (Optional)

Add free analytics:

1. **Analytics** tab in Vercel dashboard
2. Enable Web Analytics
3. Add this to `index.html` before `</head>`:

```html
<script defer src="/_vercel/insights/script.js"></script>
```

## Troubleshooting

### Issue: 404 on Assets

**Solution**: Check that `vercel.json` is present and routes are configured.

### Issue: Styles Not Loading

**Solution**: Ensure paths in HTML are relative:
```html
<!-- Correct -->
<link rel="stylesheet" href="assets/css/style.css">

<!-- Not -->
<link rel="stylesheet" href="/assets/css/style.css">
```

### Issue: Slow Build Times

**Solution**: Landing page is static HTML, should deploy in < 30 seconds. If slow:
- Check for large files in assets
- Optimize images (see SCREENSHOT_GUIDE.md)

## Vercel Configuration

The `vercel.json` file includes:
- **Security headers** (XSS protection, frame options)
- **Cache headers** for assets (1 year cache)
- **Static build** configuration

## Cost

**Free Tier Includes:**
- Unlimited deployments
- Automatic HTTPS
- 100GB bandwidth/month
- Unlimited preview deployments
- Web Analytics

**Paid Plans** (if needed later):
- Pro: $20/month (1TB bandwidth)
- Custom domains
- Advanced analytics

## Comparison: Vercel vs GitHub Pages

| Feature | Vercel | GitHub Pages |
|---------|--------|--------------|
| Custom Domain | ✅ Easy | ✅ Requires DNS setup |
| HTTPS | ✅ Automatic | ✅ Automatic |
| CDN | ✅ Global | ✅ GitHub CDN |
| Build Time | ~30s | ~2-5 min |
| Preview Deploys | ✅ Yes | ❌ No |
| Analytics | ✅ Built-in | ❌ Need Google Analytics |
| API Routes | ✅ Serverless | ❌ No |

**Recommendation**: Use Vercel for the landing page (it's faster and has better features).

## Advanced: Add Serverless Functions

If you want to add a contact form or API later:

```javascript
// api/contact.js
export default async function handler(req, res) {
  if (req.method === 'POST') {
    const { email, message } = req.body;

    // Send email or save to database

    res.status(200).json({ success: true });
  }
}
```

Then call from your landing page:
```javascript
fetch('/api/contact', {
  method: 'POST',
  body: JSON.stringify({ email, message })
});
```

## Update Deployment

Automatic on git push, or manually:

```bash
cd landing-page
vercel --prod
```

## Monitor Deployment

- **Dashboard**: https://vercel.com/dashboard
- **Deployments**: See all deploys and logs
- **Analytics**: Real-time visitor stats
- **Logs**: Real-time function logs

## Next Steps After Deployment

1. ✅ Test the live site
2. ✅ Add custom domain
3. ✅ Enable analytics
4. ✅ Add real screenshots
5. ✅ Share the URL!

## Support

- Vercel Docs: https://vercel.com/docs
- Vercel Support: https://vercel.com/support
- Community: https://github.com/vercel/vercel/discussions

---

**Your landing page is now ready to deploy to Vercel!** 🚀

Run `vercel` in the `landing-page` directory to get started.

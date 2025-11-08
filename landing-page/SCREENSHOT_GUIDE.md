# Screenshot Capture Guide

This guide helps you create professional screenshots of Data Destroyer for the landing page.

## Prerequisites

1. **Run Data Destroyer locally:**
```bash
cd /path/to/datadestroyer
docker-compose -f docker-compose.prod.enhanced.yml up -d
# OR
python manage.py runserver
```

2. **Load demo data:**
```bash
python manage.py generate_demo_data --days 30
```

3. **Create superuser (if needed):**
```bash
python manage.py createsuperuser
```

## Recommended Screenshot Specs

- **Resolution**: 1920x1080 (or 2560x1440 for retina)
- **Browser**: Chrome (for consistency)
- **Window Size**: 1440x900 or full screen
- **Format**: PNG (for quality) or WebP (for size)
- **File Size**: < 500KB per image (use compression)

## Screenshots Needed

### 1. Dashboard Overview ⭐ PRIORITY
**File**: `dashboard.png`
**Purpose**: Hero section main visual
**What to Capture**:
- Main dashboard with privacy score
- Recent activity metrics
- Charts showing data trends
- Clean, professional view

**Steps**:
1. Login to http://localhost:8000/admin/
2. Navigate to main dashboard (if available) or analytics
3. Ensure data looks realistic (not too sparse)
4. Take full-window screenshot
5. Crop to just the content area (remove browser chrome)

### 2. Data Discovery Interface
**File**: `discovery.png`
**Purpose**: Show ML classification in action
**What to Capture**:
- List of discovered data assets
- Classification labels (PII, PHI, PCI)
- Confidence scores
- Filter/search interface

**Steps**:
1. Navigate to /api/discovery/ or discovery interface
2. Show table with multiple classified items
3. Include visual indicators (badges, colors)

### 3. ML Classification Results
**File**: `ml-classification.png`
**Purpose**: Demonstrate the ML engine
**What to Capture**:
- Text being classified
- Highlighted entities
- Confidence scores
- Entity labels

**Steps**:
1. Use /api/discovery/ml/classify/ endpoint
2. Show sample text with detected entities
3. Visual highlighting of sensitive data

### 4. Policy Violations Dashboard
**File**: `violations.png`
**Purpose**: Show governance features
**What to Capture**:
- List of policy violations
- Severity levels
- Status indicators
- Violation details

### 5. Compliance Reports
**File**: `compliance.png`
**Purpose**: Show compliance features
**What to Capture**:
- GDPR/HIPAA/PCI compliance status
- Audit reports interface
- Compliance score or metrics

### 6. Settings/Configuration
**File**: `settings.png`
**Purpose**: Show configurability
**What to Capture**:
- Policy configuration
- ML model settings
- Integration options

## Capturing Screenshots

### Method 1: Browser Screenshot (Recommended)

**Chrome DevTools:**
```
1. Open Chrome DevTools (F12)
2. Cmd/Ctrl + Shift + P
3. Type "Capture screenshot"
4. Choose "Capture full size screenshot" or "Capture screenshot"
```

**Advantages**:
- Consistent rendering
- Can set custom viewport size
- Built-in, no extra tools needed

### Method 2: Browser Extensions

**Awesome Screenshot** (Chrome/Firefox):
- Full page screenshots
- Annotation tools
- Blur sensitive data
- Instant edit and save

**Nimbus Screenshot**:
- Video recording option
- Cloud storage
- Built-in editor

### Method 3: OS Screenshot Tools

**macOS**:
- `Cmd + Shift + 4` - Select area
- `Cmd + Shift + 5` - Screenshot options
- **CleanShot X** (paid) - Professional annotations

**Windows**:
- `Win + Shift + S` - Snipping tool
- **ShareX** (free) - Advanced capture tool

**Linux**:
- **Flameshot** - Powerful screenshot tool
- **GNOME Screenshot** - Built-in tool

## Preparing Screenshots

### 1. Clean Up Sensitive Data

Before capturing:
- Use demo data, not real data
- Check for any sensitive information
- Replace real names with fictional ones
- Verify no API keys or secrets visible

### 2. Make It Look Professional

- **Remove clutter**: Close unnecessary tabs/windows
- **Consistent styling**: Use same theme/colors throughout
- **Good data**: Not too empty, not too crowded
- **Readable text**: Zoom appropriately (90-100%)
- **Hide UI elements**: Personal bookmarks, extensions, etc.

### 3. Optimize Images

**Using ImageMagick:**
```bash
# Install
brew install imagemagick  # macOS
sudo apt install imagemagick  # Linux

# Resize to 1200px wide (maintains aspect ratio)
convert dashboard.png -resize 1200x -quality 85 dashboard-optimized.png

# Add subtle shadow
convert dashboard.png \
  \( +clone -background black -shadow 60x5+0+5 \) \
  +swap -background none -layers merge +repage \
  dashboard-shadow.png
```

**Using Online Tools:**
- **TinyPNG** (tinypng.com) - Excellent compression
- **Squoosh** (squoosh.app) - Google's image optimizer
- **Compressor.io** - Multiple format support

**Target file sizes:**
- Hero image: < 300KB
- Section images: < 200KB
- Thumbnails: < 100KB

### 4. Add to Landing Page

**Replace preview in `index.html`:**

```html
<!-- Replace the .dashboard-preview div with: -->
<div class="hero-visual">
    <img src="assets/images/dashboard.png"
         alt="Data Destroyer Dashboard showing privacy score and data classification metrics"
         class="dashboard-screenshot"
         loading="lazy">
</div>
```

**Add CSS in `assets/css/style.css`:**

```css
.dashboard-screenshot {
    width: 100%;
    max-width: 100%;
    height: auto;
    border-radius: 1rem;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1),
                0 10px 10px -5px rgba(0, 0, 0, 0.04);
    animation: float 6s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-20px); }
}
```

## Creating a Screenshot Gallery

Add an image gallery section to showcase multiple features:

```html
<!-- Add after industries section in index.html -->
<section class="screenshot-gallery">
    <div class="container">
        <div class="section-header">
            <h2>See Data Destroyer in Action</h2>
            <p>Explore the platform's key features</p>
        </div>
        <div class="gallery-grid">
            <div class="gallery-item">
                <img src="assets/images/discovery.png" alt="Data Discovery Interface">
                <h3>Automated Discovery</h3>
                <p>Find sensitive data across all your systems</p>
            </div>
            <div class="gallery-item">
                <img src="assets/images/ml-classification.png" alt="ML Classification">
                <h3>AI Classification</h3>
                <p>98%+ accurate ML-powered data classification</p>
            </div>
            <div class="gallery-item">
                <img src="assets/images/compliance.png" alt="Compliance Dashboard">
                <h3>Compliance Reports</h3>
                <p>One-click GDPR, HIPAA, and PCI reports</p>
            </div>
        </div>
    </div>
</section>
```

**Add gallery CSS:**

```css
.screenshot-gallery {
    padding: 4rem 0;
    background: var(--bg-light);
}

.gallery-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 2rem;
}

.gallery-item {
    background: white;
    border-radius: 1rem;
    overflow: hidden;
    box-shadow: var(--shadow);
    transition: transform 0.3s;
}

.gallery-item:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-lg);
}

.gallery-item img {
    width: 100%;
    height: 250px;
    object-fit: cover;
    border-bottom: 1px solid var(--border);
}

.gallery-item h3 {
    padding: 1.5rem 1.5rem 0.5rem;
    font-size: 1.25rem;
}

.gallery-item p {
    padding: 0 1.5rem 1.5rem;
    color: var(--text-secondary);
}

@media (max-width: 768px) {
    .gallery-grid {
        grid-template-columns: 1fr;
    }
}
```

## Creating Animated GIFs

For showing interactions (optional but impressive):

**Using ScreenToGif (Windows):**
1. Download from screentogif.com
2. Record specific interaction
3. Edit frames
4. Export as optimized GIF

**Using Gifox (macOS):**
1. Download from gifox.io
2. Record screen area
3. Auto-optimize
4. Save

**Using LICEcap (Cross-platform):**
1. Download from cockos.com/licecap
2. Position window
3. Record
4. Save as GIF

**Example interactions to record:**
- Typing in the ML classification demo
- Filtering data in discovery interface
- Generating a compliance report

**Optimize GIFs:**
```bash
# Using gifsicle
gifsicle -O3 --colors 128 input.gif -o output.gif

# Reduce to 10 FPS
gifsicle --delay=10 --colors 128 -O3 input.gif -o output.gif
```

## Screenshot Checklist

Before publishing:

- [ ] All screenshots are 1200px+ wide
- [ ] No sensitive/real data visible
- [ ] Consistent browser/theme across all images
- [ ] Optimized file sizes (< 300KB each)
- [ ] Proper alt text in HTML
- [ ] Images load with lazy loading
- [ ] Responsive on mobile (test at 375px width)
- [ ] All images in `assets/images/` directory
- [ ] Referenced correctly in HTML/CSS
- [ ] Copyright/attribution if using stock images

## Alternative: Use Figma Mockups

If you can't run the app yet or want pixel-perfect designs:

1. **Create in Figma** (figma.com)
2. Design dashboard mockups based on your wireframes
3. Export as PNG (2x for retina)
4. Looks professional even without real app

**Figma Templates:**
- Search "SaaS Dashboard" in Figma Community
- Customize colors to match your brand
- Add your metrics and data

## Quick Template (If No Screenshots Yet)

Use the existing SVG preview in the landing page and add this note:

```html
<div class="preview-note">
    <p>
        📸 Full application screenshots coming soon!
        <a href="https://github.com/cLeffNote44/datadestroyer">Deploy now</a>
        to see the platform in action.
    </p>
</div>
```

This keeps the landing page professional while you capture real screenshots.

---

## Tips for Best Results

1. **Consistency is key** - Use same browser, window size, theme
2. **Tell a story** - Screenshots should show workflow progression
3. **Highlight features** - Use arrows/annotations to point out key elements
4. **Keep it clean** - Remove distractions, focus on the feature
5. **Update regularly** - As features evolve, update screenshots

**Questions?** Check the [Landing Page README](README.md) for more details.

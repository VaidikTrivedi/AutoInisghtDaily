# Frontend Requirements Document

## AutoInsightDaily - Web Dashboard

### Overview

A web-based dashboard for managing the AutoInsightDaily news automation pipeline. The frontend will provide a visual interface to control news fetching, AI summarization, image generation, and Instagram posting workflows.

---

## 1. Core Features

### 1.1 Dashboard Home

| Feature | Description |
|---------|-------------|
| Pipeline Status | Real-time status of the automation pipeline (Idle, Running, Completed, Error) |
| Quick Actions | One-click buttons for common operations (Generate Posts, Upload, Post to Instagram) |
| Recent Activity | Timeline showing recent operations with timestamps |
| Token Usage Stats | Display total prompt tokens, completion tokens, and API costs |

### 1.2 News Management

#### 1.2.1 News Sources Configuration
- **View RSS Sources**: List all configured news sources with categories
- **Add/Edit/Remove Sources**: CRUD operations for RSS feed URLs
- **Category Management**: Manage categories (Finance, Tech, Politics, Sports, etc.)
- **Source Health Check**: Verify if RSS feeds are accessible

#### 1.2.2 News Fetching
- **Fetch Headlines**: Button to manually trigger headline collection
- **Headlines Preview**: Display fetched headlines in a card/list view with:
  - Title
  - Source/Category badge
  - Original link
  - Fetch timestamp
- **Select/Deselect Headlines**: Choose which headlines to process
- **Headline Limit Slider**: Adjust number of headlines to fetch (1-15)

### 1.3 AI Processing

#### 1.3.1 AI Provider Settings
- **Provider Toggle**: Switch between Ollama (local) and OpenRouter (cloud)
- **Model Selection**: Dropdown to select AI models:
  - Summary Model (llama3, qwen, gemma4, etc.)
  - Translation Model (translategemma, etc.)
  - Image Generation Model (flux2-klein, z-image-turbo, riverflow, etc.)
- **API Key Management**: Secure input for OpenRouter API key
- **Connection Test**: Verify AI provider connectivity

#### 1.3.2 Summarization
- **Auto-Summarize All**: Process all selected headlines
- **Individual Summarize**: Summarize one headline at a time
- **Summary Preview**: Show original vs. summarized text side-by-side
- **Edit Summary**: Manually edit AI-generated summaries
- **Hashtag Editor**: View/edit extracted hashtags
- **Regenerate**: Re-run summarization for a specific item

#### 1.3.3 Translation (Optional)
- **Enable/Disable Hindi Translation**: Toggle for bilingual posts
- **Translation Preview**: Show English and Hindi versions
- **Edit Translations**: Manual correction of translations

### 1.4 Image Generation

#### 1.4.1 Image Preview & Editor
- **Generated Images Grid**: Thumbnail gallery of all generated images
- **Full-Size Preview**: Click to view image at 1080x1080
- **Image Editor**:
  - Adjust text position (drag & drop)
  - Change font size
  - Modify text color
  - Edit headline/summary text overlay
- **Regenerate Image**: Re-generate specific image with new AI prompt
- **Download Individual**: Save single image locally

#### 1.4.2 Theme Customization
- **Theme Selector**: Choose from predefined themes (Finance, Tech, Politics, General)
- **Custom Theme Creator**:
  - Background color picker
  - Text color picker
  - Accent color picker
- **Preview Theme**: Live preview of theme changes

#### 1.4.3 Background Generation
- **AI Background Toggle**: Enable/disable AI-generated backgrounds
- **Background Prompt Editor**: View/edit the prompt used for background generation
- **Upload Custom Background**: Use own image as background
- **Background Library**: Save and reuse favorite backgrounds

### 1.5 Post Management

#### 1.5.1 Post Preview
- **Carousel Preview**: Swipeable carousel showing all images in order
- **Reorder Images**: Drag-and-drop to change image order
- **Remove from Post**: Exclude specific images from the carousel
- **Caption Editor**: 
  - View auto-generated caption (hashtags + sources)
  - Edit caption text
  - Character count (Instagram limit: 2,200)
- **Mobile Preview**: Simulate how post will look on Instagram

#### 1.5.2 Staging & Upload
- **Upload to Stage**: Button to upload images to staging server
- **Staging Status**: Show upload progress with checkmarks
- **Staged Images List**: View images currently on staging server with URLs
- **Cleanup Staging**: Remove all images from staging server

#### 1.5.3 Instagram Publishing
- **Account Connection**: Display connected Instagram account info
- **Publish Button**: Post carousel to Instagram
- **Publishing Progress**: Real-time status (Creating containers → Carousel → Publishing)
- **Success/Error Notification**: Clear feedback on post result
- **View on Instagram**: Link to published post

### 1.6 History & Analytics

#### 1.6.1 Post History
- **Past Posts List**: Table/cards showing previously generated posts
- **View Post Details**: Expand to see headlines, summaries, images
- **Re-use Content**: Clone a previous post as template
- **Delete History**: Remove old records

#### 1.6.2 Analytics Dashboard
- **Token Usage Graph**: Line chart of API token usage over time
- **Posts Per Day/Week**: Bar chart of posting frequency
- **Source Distribution**: Pie chart of news categories used
- **AI Processing Time**: Average duration for summarization/image generation

---

## 2. Settings & Configuration

### 2.1 General Settings
| Setting | Type | Description |
|---------|------|-------------|
| Image Directory | Text Input | Path to save generated images |
| Default Headline Limit | Number | Default number of headlines to fetch |
| Auto-Cleanup | Toggle | Automatically clean staging after successful post |

### 2.2 Font Configuration
- Regular Font Path
- Bold Font Path
- Hindi Regular Font Path
- Hindi Bold Font Path
- Font Preview

### 2.3 Instagram API Configuration
- Access Token (secure/masked input)
- Instagram User ID
- Graph API Version
- Connection Test Button

### 2.4 Staging Server
- Staging URL
- Test Upload Button
- Server Status Indicator

---

## 3. UI/UX Requirements

### 3.1 Layout
- **Responsive Design**: Works on desktop (primary), tablet, and mobile
- **Sidebar Navigation**: Collapsible menu for main sections
- **Dark/Light Mode**: Theme toggle
- **Persistent Header**: App logo, status indicator, settings access

### 3.2 Components
- **Loading States**: Spinners/skeletons during async operations
- **Toast Notifications**: Success, error, warning messages
- **Confirmation Modals**: For destructive actions (delete, cleanup, post)
- **Progress Bars**: For multi-step operations
- **Drag & Drop**: For image reordering and file uploads

### 3.3 Accessibility
- Keyboard navigation support
- ARIA labels for screen readers
- Sufficient color contrast
- Focus indicators

---

## 4. Technical Requirements

### 4.1 Frontend Stack (Recommended)
| Technology | Purpose |
|------------|---------|
| **React / Next.js** | UI Framework |
| **TypeScript** | Type safety |
| **Tailwind CSS** | Styling |
| **Shadcn/UI** | Component library |
| **React Query / SWR** | Data fetching & caching |
| **Zustand / Redux** | State management |
| **React Hook Form** | Form handling |

### 4.2 Backend API Requirements
The frontend will need a REST/GraphQL API with these endpoints:

#### News Endpoints
```
GET    /api/sources          - List all RSS sources
POST   /api/sources          - Add new source
PUT    /api/sources/:id      - Update source
DELETE /api/sources/:id      - Delete source
POST   /api/headlines/fetch  - Fetch headlines from sources
GET    /api/headlines        - Get fetched headlines
```

#### AI Processing Endpoints
```
POST   /api/summarize        - Summarize a headline
POST   /api/summarize/batch  - Summarize multiple headlines
POST   /api/translate        - Translate text to Hindi
GET    /api/ai/status        - Check AI provider status
PUT    /api/ai/settings      - Update AI settings
```

#### Image Endpoints
```
POST   /api/images/generate           - Generate image for a headline
POST   /api/images/generate-background - Generate AI background
PUT    /api/images/:id                - Update image (reorder, edit)
DELETE /api/images/:id                - Delete image
GET    /api/images                    - List generated images
```

#### Publishing Endpoints
```
POST   /api/staging/upload    - Upload images to staging
GET    /api/staging/images    - List staged images
DELETE /api/staging/cleanup   - Clean staging server
POST   /api/instagram/post    - Post to Instagram
GET    /api/instagram/status  - Check posting status
```

#### Settings Endpoints
```
GET    /api/settings          - Get all settings
PUT    /api/settings          - Update settings
POST   /api/settings/test-ig  - Test Instagram connection
POST   /api/settings/test-ai  - Test AI connection
```

### 4.3 Real-time Updates
- **WebSocket / SSE**: For live pipeline status updates
- **Polling Fallback**: For environments without WebSocket support

### 4.4 Security
- API key encryption in frontend storage
- HTTPS only
- CORS configuration
- Rate limiting awareness

---

## 5. User Flows

### 5.1 Primary Flow: Generate & Post
```
1. User clicks "Fetch Headlines"
2. System fetches from all RSS sources
3. User reviews and selects headlines (or uses all)
4. User clicks "Generate Posts"
5. System summarizes each headline
6. System generates images with AI backgrounds
7. User previews carousel, makes edits if needed
8. User clicks "Upload to Staging"
9. Images are uploaded to staging server
10. User reviews staged images
11. User clicks "Post to Instagram"
12. System creates carousel and publishes
13. Success notification with link to post
14. Auto-cleanup of staging (if enabled)
```

### 5.2 Quick Post Flow
```
1. User clicks "Quick Post" on dashboard
2. System runs full pipeline automatically
3. User sees progress in real-time
4. Final confirmation before posting
5. One-click publish
```

### 5.3 Edit & Repost Flow
```
1. User views post history
2. User selects a previous post
3. User edits summaries/images
4. User regenerates specific images
5. User posts updated version
```

---

## 6. Mockup Wireframes

### 6.1 Dashboard Layout
```
┌─────────────────────────────────────────────────────────────┐
│  🗞️ AutoInsightDaily                    [⚙️] [🌙] [👤]     │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│ 📊 Home  │  Pipeline Status: ✅ Idle                        │
│          │  ┌─────────────────────────────────────────────┐ │
│ 📰 News  │  │  [Fetch Headlines] [Generate] [Post]       │ │
│          │  └─────────────────────────────────────────────┘ │
│ 🤖 AI    │                                                  │
│          │  Recent Activity                    Token Usage  │
│ 🖼️ Images│  ├─ 10:30 AM - Posted carousel    ┌──────────┐  │
│          │  ├─ 10:25 AM - Generated 8 imgs   │ 📊 1,234 │  │
│ 📤 Post  │  ├─ 10:20 AM - Fetched headlines  │  tokens  │  │
│          │  └─ 10:15 AM - Started pipeline   └──────────┘  │
│ 📈 Stats │                                                  │
│          │                                                  │
│ ⚙️ Settings│                                                │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

### 6.2 News Management
```
┌─────────────────────────────────────────────────────────────┐
│  📰 News Headlines                    [🔄 Fetch] [Limit: 10]│
├─────────────────────────────────────────────────────────────┤
│ ☑️ | Finance | CNBC                                         │
│    "Markets rally as Fed signals rate cuts ahead"           │
│    [View] [Summarize] [Remove]                              │
├─────────────────────────────────────────────────────────────┤
│ ☑️ | Tech | TechCrunch                                      │
│    "Apple announces new AI features for iOS 20"             │
│    [View] [Summarize] [Remove]                              │
├─────────────────────────────────────────────────────────────┤
│ ☑️ | Politics | BBC                                         │
│    "UN Security Council meets on climate emergency"         │
│    [View] [Summarize] [Remove]                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│         [Select All] [Deselect All] [Process Selected →]   │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Image Gallery
```
┌─────────────────────────────────────────────────────────────┐
│  🖼️ Generated Images                      [Download All 📥] │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │  IMG 1  │  │  IMG 2  │  │  IMG 3  │  │  IMG 4  │        │
│  │ Finance │  │  Tech   │  │Politics │  │ Sports  │        │
│  │   ✏️ 🔄  │  │   ✏️ 🔄  │  │   ✏️ 🔄  │  │   ✏️ 🔄  │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │  IMG 5  │  │  IMG 6  │  │  IMG 7  │  │  IMG 8  │        │
│  │  India  │  │   AI    │  │Innovation│  │ Positive│        │
│  │   ✏️ 🔄  │  │   ✏️ 🔄  │  │   ✏️ 🔄  │  │   ✏️ 🔄  │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                             │
│              [Upload to Staging →]                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Future Enhancements (Phase 2)

- **Scheduling**: Schedule posts for specific times
- **Multi-Account Support**: Manage multiple Instagram accounts
- **Template System**: Save and reuse image templates
- **Bulk Operations**: Process weeks of content at once
- **AI Prompt Library**: Save effective prompts for reuse
- **Content Calendar**: Visual calendar view of scheduled posts
- **Team Collaboration**: Multi-user access with roles
- **Webhook Integrations**: Notify external services on events
- **Mobile App**: Native iOS/Android companion app

---

## 8. Development Phases

### Phase 1: MVP (4-6 weeks)
- Dashboard with pipeline status
- News fetching and listing
- Basic summarization UI
- Image generation and preview
- Manual posting flow

### Phase 2: Enhanced UX (3-4 weeks)
- Image editor
- Theme customization
- Post history
- Settings management

### Phase 3: Analytics & Polish (2-3 weeks)
- Analytics dashboard
- Performance optimizations
- Error handling improvements
- Documentation

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Time to generate post | < 5 minutes (vs CLI) |
| User errors | Reduce by 80% |
| Pipeline completion rate | > 95% |
| User satisfaction | 4.5/5 rating |

---

*Document Version: 1.0*  
*Last Updated: April 29, 2026*  
*Author: AutoInsightDaily Development Team*

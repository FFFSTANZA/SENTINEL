# Senytl Documentation Website

This directory contains the complete documentation website for the Senytl testing framework.

## Structure

```
web/
├── index.html              # Homepage with features overview
├── css/
│   └── styles.css         # Main stylesheet with responsive design
├── js/
│   └── main.js           # Interactive functionality and animations
├── docs/                 # Detailed documentation pages
│   ├── installation.html # Installation guide
│   ├── quickstart.html   # Quick start tutorial
│   ├── testing.html      # Testing basics and pytest integration
│   ├── performance.html  # Performance testing and benchmarking
│   ├── state.html        # State persistence and replay
│   ├── coverage.html     # Coverage tracking and quality metrics
│   └── cli.html          # Command-line interface reference
└── examples/             # Practical examples and tutorials
    └── basic-testing.html # Basic agent testing example
```

## Features

### Design
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Dark Mode Support**: Automatic dark mode based on system preferences
- **Modern UI**: Clean, professional design with smooth animations
- **Accessible**: WCAG compliant with proper focus management and semantic HTML

### Navigation
- **Sticky Navigation**: Fixed header with smooth scrolling
- **Breadcrumb Navigation**: Clear page hierarchy
- **Mobile Menu**: Collapsible hamburger menu for mobile devices
- **Internal Links**: Cross-referenced documentation with working internal links

### Content
- **Comprehensive**: Covers all major Senytl features and capabilities
- **Code Examples**: Extensive code examples with syntax highlighting
- **Best Practices**: Practical advice and recommendations
- **Progressive Disclosure**: Information organized from basic to advanced topics

### Interactive Features
- **Copy Code**: Click-to-copy functionality for code blocks
- **Smooth Scrolling**: Animated navigation between sections
- **Animations**: Fade-in animations for better user experience
- **Search Ready**: Structure prepared for search functionality

## Building and Deployment

### Local Development
1. Open `index.html` in a web browser
2. All files are static and can be served from any web server
3. For best results, serve from a local web server to avoid CORS issues

### Deployment Options
- **GitHub Pages**: Push to a `gh-pages` branch or use `/docs` folder
- **Netlify**: Drag and drop the `web` folder
- **Vercel**: Deploy as a static site
- **AWS S3**: Upload to an S3 bucket with static website hosting
- **Any Web Server**: Copy all files to web server root

### Customization
- **Styling**: Edit `css/styles.css` to modify appearance
- **Content**: Edit HTML files to update documentation
- **Branding**: Update logo, colors, and branding in CSS variables
- **Navigation**: Modify navigation structure in each HTML file

## Content Guidelines

### Writing Style
- **Clear and Concise**: Use simple, direct language
- **Code-First**: Lead with code examples, then explain
- **Practical Focus**: Emphasize real-world usage scenarios
- **Progressive**: Start with basics, build to advanced topics

### Code Examples
- **Complete**: Include imports and full function definitions
- **Executable**: Code examples should be runnable
- **Commented**: Include comments explaining key concepts
- **Varied**: Show different approaches and use cases

### Technical Accuracy
- **Up-to-date**: Keep examples current with latest Senytl version
- **Tested**: Verify all code examples work correctly
- **Comprehensive**: Cover edge cases and error handling
- **Best Practices**: Demonstrate recommended patterns

## Browser Support

- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **CSS Grid**: Used for responsive layouts
- **CSS Custom Properties**: Used for theming and variables
- **JavaScript ES6+**: Used for interactive features
- **Progressive Enhancement**: Core content accessible without JavaScript

## Performance

- **Optimized Assets**: Compressed CSS and JavaScript
- **Efficient Loading**: Lazy loading for non-critical resources
- **Minimal Dependencies**: Only Google Fonts as external dependency
- **Fast Rendering**: Critical CSS inlined, minimal JavaScript

## Accessibility

- **Semantic HTML**: Proper use of heading hierarchy and landmarks
- **Keyboard Navigation**: Full keyboard accessibility
- **Screen Readers**: Compatible with assistive technologies
- **Color Contrast**: WCAG AA compliant color combinations
- **Focus Management**: Clear focus indicators and logical tab order

## SEO

- **Meta Tags**: Comprehensive meta descriptions and titles
- **Structured Data**: Schema.org markup for better search results
- **Internal Linking**: Cross-referenced documentation for better crawling
- **Performance**: Fast loading times for better search rankings

## Maintenance

### Regular Updates
- Keep documentation synchronized with Senytl releases
- Update code examples to match current API
- Review and refresh best practices
- Monitor and fix broken links

### Content Reviews
- Technical accuracy review
- Code example testing
- Link validation
- Accessibility audit
- Performance monitoring

## Contributing

To contribute to the documentation:

1. **Content Updates**: Edit HTML files directly
2. **Style Changes**: Modify CSS variables and rules
3. **New Pages**: Follow existing structure and naming conventions
4. **Code Examples**: Ensure all examples are tested and current
5. **Links**: Verify internal and external links work correctly

## License

This documentation is part of the Senytl project and follows the same MIT license.
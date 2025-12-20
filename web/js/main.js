// Mobile navigation toggle
document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');

    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });

        // Close menu when clicking on a link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            });
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!hamburger.contains(event.target) && !navMenu.contains(event.target)) {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            }
        });
    }
});

// Smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const offsetTop = target.offsetTop - 80; // Account for fixed navbar
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
});

// Navbar scroll effect
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 100) {
        navbar.style.background = 'rgba(255, 255, 255, 0.98)';
        navbar.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
    } else {
        navbar.style.background = 'rgba(255, 255, 255, 0.95)';
        navbar.style.boxShadow = 'none';
    }
});

// Intersection Observer for animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-fade-in-up');
        }
    });
}, observerOptions);

// Observe elements for animation
document.addEventListener('DOMContentLoaded', function() {
    // Observe feature cards
    document.querySelectorAll('.feature-card').forEach(card => {
        observer.observe(card);
    });

    // Observe steps
    document.querySelectorAll('.step').forEach(step => {
        observer.observe(step);
    });

    // Observe doc categories
    document.querySelectorAll('.doc-category').forEach(category => {
        observer.observe(category);
    });

    // Observe example cards
    document.querySelectorAll('.example-card').forEach(card => {
        observer.observe(card);
    });
});

// Copy code functionality
function copyCode(button) {
    const codeBlock = button.parentElement.querySelector('pre code');
    const text = codeBlock.textContent;
    
    navigator.clipboard.writeText(text).then(function() {
        // Show success feedback
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.style.background = '#10b981';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = '';
        }, 2000);
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            const originalText = button.textContent;
            button.textContent = 'Copied!';
            button.style.background = '#10b981';
            
            setTimeout(() => {
                button.textContent = originalText;
                button.style.background = '';
            }, 2000);
        } catch (err) {
            console.error('Fallback copy failed: ', err);
        }
        document.body.removeChild(textArea);
    });
}

// Add copy buttons to code blocks
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.code-block pre').forEach(pre => {
        const button = document.createElement('button');
        button.className = 'copy-btn';
        button.textContent = 'Copy';
        button.onclick = () => copyCode(button);
        
        const wrapper = pre.parentElement;
        wrapper.style.position = 'relative';
        wrapper.appendChild(button);
    });
});

// Search functionality (for future implementation)
function initializeSearch() {
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    
    if (!searchInput || !searchResults) return;
    
    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            searchResults.innerHTML = '';
            searchResults.style.display = 'none';
            return;
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });
    
    function performSearch(query) {
        // This would typically search through documentation content
        // For now, we'll show a placeholder
        const results = [
            { title: 'Getting Started', url: '#getting-started', type: 'guide' },
            { title: 'pytest Integration', url: 'docs/testing.html', type: 'doc' },
            { title: 'Performance Testing', url: 'docs/performance.html', type: 'doc' }
        ].filter(item => item.title.toLowerCase().includes(query.toLowerCase()));
        
        displaySearchResults(results);
    }
    
    function displaySearchResults(results) {
        if (results.length === 0) {
            searchResults.innerHTML = '<div class="search-no-results">No results found</div>';
        } else {
            searchResults.innerHTML = results.map(result => `
                <div class="search-result" onclick="window.location.href='${result.url}'">
                    <div class="search-result-title">${result.title}</div>
                    <div class="search-result-type">${result.type}</div>
                </div>
            `).join('');
        }
        searchResults.style.display = 'block';
    }
}

// Initialize search when DOM is ready
document.addEventListener('DOMContentLoaded', initializeSearch);

// Theme toggle functionality (for future implementation)
function initializeThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    
    if (!themeToggle) return;
    
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    
    themeToggle.addEventListener('click', function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    });
}

// Initialize theme toggle
document.addEventListener('DOMContentLoaded', initializeThemeToggle);

// Performance monitoring for documentation page load
window.addEventListener('load', function() {
    // Log performance metrics for monitoring
    if ('performance' in window) {
        const perfData = performance.getEntriesByType('navigation')[0];
        console.log('Documentation page load time:', perfData.loadEventEnd - perfData.loadEventStart, 'ms');
    }
});

// Analytics tracking (placeholder for future implementation)
function trackEvent(category, action, label) {
    // This would integrate with your analytics service
    console.log('Analytics Event:', { category, action, label });
    
    // Example Google Analytics 4 integration:
    // gtag('event', action, {
    //     event_category: category,
    //     event_label: label
    // });
}

// Track documentation page views
document.addEventListener('DOMContentLoaded', function() {
    trackEvent('Documentation', 'page_view', 'index');
    
    // Track button clicks
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', function() {
            trackEvent('UI', 'button_click', this.textContent.trim());
        });
    });
    
    // Track navigation clicks
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function() {
            trackEvent('Navigation', 'nav_click', this.getAttribute('href'));
        });
    });
});

// Error handling for JavaScript
window.addEventListener('error', function(event) {
    console.error('JavaScript error:', event.error);
    // In production, you might want to send this to an error tracking service
    // trackEvent('Error', 'javascript_error', event.error.message);
});

// Service Worker registration (for future PWA features)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Register service worker for offline functionality
        // navigator.serviceWorker.register('/sw.js')
        //     .then(registration => console.log('SW registered'))
        //     .catch(error => console.log('SW registration failed'));
    });
}
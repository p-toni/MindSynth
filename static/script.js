class KnowledgeSearch {
    constructor() {
        this.searchInput = document.getElementById('searchInput');
        this.results = document.getElementById('results');
        this.status = document.getElementById('searchStatus');
        this.panel = document.getElementById('contentPanel');
        this.panelTitle = document.getElementById('panelTitle');
        this.panelContent = document.getElementById('panelContent');
        this.closePanel = document.getElementById('closePanel');
        this.searchTimeout = null;
        this.previousActiveElement = null;
        
        console.log('KnowledgeSearch constructor - elements found:', {
            searchInput: !!this.searchInput,
            results: !!this.results,
            status: !!this.status,
            panel: !!this.panel,
            panelTitle: !!this.panelTitle,
            panelContent: !!this.panelContent,
            closePanel: !!this.closePanel
        });
        
        this.init();
    }

    init() {
        console.log('Initializing KnowledgeSearch...');
        
        this.searchInput.addEventListener('input', () => this.handleSearch());
        this.closePanel.addEventListener('click', () => this.hidePanel());
        
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') this.hidePanel();
        });
        
        document.addEventListener('click', e => {
            if (this.panel.classList.contains('active') && 
                !this.panel.contains(e.target) && 
                !e.target.classList.contains('dot')) {
                this.hidePanel();
            }
        });

        this.searchInput.setAttribute('aria-label', 'Search knowledge');
        
        // Keyboard navigation for dots
        this.results.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ' ') {
                const focusedDot = document.activeElement;
                if (focusedDot && focusedDot.classList.contains('dot')) {
                    focusedDot.click();
                    e.preventDefault();
                }
            }
        });
        
        console.log('KnowledgeSearch initialized');
    }

    handleSearch() {
        clearTimeout(this.searchTimeout);
        const query = this.searchInput.value.trim();
        
        if (!query) {
            this.showWelcome();
            this.status.textContent = '';
            return;
        }
        
        this.status.textContent = 'SEARCHING...';
        this.searchTimeout = setTimeout(() => this.performSearch(query), 300);
    }

    async performSearch(query) {
        try {
            const response = await fetch(`/search?q=${encodeURIComponent(query)}&limit=30&offset=0`);
            const payload = await response.json();
            this.displayResults(payload.results || [], query, payload.total || 0);
        } catch (error) {
            console.error('Search error:', error);
            this.status.textContent = 'SEARCH ERROR';
        } finally {
            this.status.textContent = '';
        }
    }

    displayResults(results, query, total) {
        console.log('Displaying results:', results.length, 'total:', total);
        
        if (!results.length) {
            this.results.innerHTML = `
                <div class="no-results">
                    <h3>NO RESULTS FOUND</h3>
                    <p>Try different search terms or verify your knowledge base</p>
                </div>`;
            return;
        }

        const html = `
            <div class="dots-grid">
                ${results.map(result => {
                    const size = Math.round(8 + result.similarity * 16);
                    const matchPercent = Math.round(result.similarity * 100);
                    const summary = this.generateSummary(result.title);
                    const tags = this.generateTags(result.title);
                    
                    // Add staggered delay for natural flow
                    const delay = results.indexOf(result) * 0.1;
                    
                    return `
                        <div class="dot" 
                             role="button" 
                             tabindex="0" 
                             aria-label="Open ${this.escapeHtml(result.title)} (${matchPercent}% match)"
                             data-filename="${result.file}"
                             onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();event.target.click()}"
                             style="width:${size}px;height:${size}px;background:hsl(${Math.round(result.similarity * 120)}, 30%, ${20 + result.similarity * 40}%);animation-delay:${delay}s"
                             data-tooltip-content='{"title":"${this.escapeHtml(result.title)}","summary":"${summary}","match":"${matchPercent}","tags":${JSON.stringify(tags)}}'>
                        </div>`;
                }).join('')}
            </div>`;

        const more = total > results.length ? 
            `<div style="text-align:center;margin-top:16px;">
                <button id="showMore" class="close-panel" style="font-size:14px">Show more</button>
             </div>` : '';

        this.results.innerHTML = html + more;
        this.addTooltipListeners();
        this.addDotClickListeners();
        
        const btn = document.getElementById('showMore');
        if (btn) {
            btn.addEventListener('click', () => alert('Pagination UI placeholder'));
        }
        
        console.log('Results displayed, dots created:', document.querySelectorAll('.dot').length);
    }

    showWelcome() {
        this.results.innerHTML = '';
    }

    async showContent(filename) {
        console.log('showContent called with filename:', filename);
        try {
            const response = await fetch(`/content/${encodeURIComponent(filename)}`);
            const data = await response.json();
            
            console.log('Content response:', data);
            
            if (data.error) {
                alert('Content not found');
                return;
            }
            
            this.panelTitle.textContent = data.title;
            this.panelContent.innerHTML = data.content;
            this.showPanel();
            this.loadTwitterWidgets();
        } catch (error) {
            console.error('Content load error:', error);
            alert('Failed to load content');
        }
    }

    showPanel() {
        console.log('showPanel called');
        this.previousActiveElement = document.activeElement;
        this.panel.classList.add('open');
        this.panel.focus();
        console.log('Panel should now be visible');
    }

    hidePanel() {
        console.log('hidePanel called');
        this.panel.classList.remove('open');
        if (this.previousActiveElement) {
            this.previousActiveElement.focus();
        } else {
            this.searchInput.focus();
        }
        console.log('Panel should now be hidden');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    generateSummary(title) {
        const summaries = {
            'Machine Learning Fundamentals': 'AI algorithms that learn from data',
            'Design Principles': 'Communication through simplicity and consistency',
            'Productivity Systems': 'Time management and task organization systems',
            'Philosophy of Technology': 'How tools shape human thought',
            'The Craft of Writing': 'Clear communication through deliberate word choice',
            'Mindfulness Practice': 'Present-moment awareness without judgment',
            'Sustainable Living': 'Meeting needs without compromising the future',
            'Music Theory Basics': 'Language for understanding how music works',
            'Financial Independence': 'Building wealth to live without employment',
            'Cooking Fundamentals': 'Understanding ingredients and flavor techniques',
            'Effective Learning Strategies': 'Active recall and spaced repetition',
            'Minimalism Philosophy': 'Making room for what matters',
            'Exercise Physiology': 'How the body adapts to physical stress',
            'Urban Planning Principles': 'Designing walkable cities for people',
            'Photography Composition': 'Guiding attention through visual hierarchy',
            'Decision-Making Frameworks': 'Processes to overcome cognitive biases',
            'Renewable Energy Technologies': 'Clean energy through solar, wind, storage',
            'Emotional Intelligence': 'Managing emotions for better relationships',
            'Systems Thinking': 'Finding leverage points for change',
            'The Creative Process': 'Innovation through preparation and play',
            'Welcome to Your Knowledge Base': 'Getting started with semantic search'
        };
        return summaries[title] || 'Key concepts and practical applications';
    }

    generateTags(title) {
        const tags = {
            'Machine Learning Fundamentals': ['AI', 'data'],
            'Design Principles': ['visual', 'design'],
            'Productivity Systems': ['time', 'efficiency'],
            'Philosophy of Technology': ['ethics', 'society'],
            'The Craft of Writing': ['writing', 'clarity'],
            'Mindfulness Practice': ['wellness', 'meditation'],
            'Sustainable Living': ['environment', 'lifestyle'],
            'Music Theory Basics': ['music', 'harmony'],
            'Financial Independence': ['money', 'freedom'],
            'Cooking Fundamentals': ['food', 'technique'],
            'Effective Learning Strategies': ['learning', 'memory'],
            'Minimalism Philosophy': ['lifestyle', 'clarity'],
            'Exercise Physiology': ['fitness', 'health'],
            'Urban Planning Principles': ['cities', 'design'],
            'Photography Composition': ['visual', 'art'],
            'Decision-Making Frameworks': ['thinking', 'process'],
            'Renewable Energy Technologies': ['energy', 'tech'],
            'Emotional Intelligence': ['psychology', 'leadership'],
            'Systems Thinking': ['complexity', 'change'],
            'The Creative Process': ['creativity', 'innovation'],
            'Welcome to Your Knowledge Base': ['search', 'docs']
        };
        return tags[title] || ['knowledge', 'reference'];
    }

    addTooltipListeners() {
        document.querySelectorAll('.dot').forEach(dot => {
            dot.addEventListener('mouseenter', e => this.showTooltip(e));
            dot.addEventListener('mouseleave', () => this.hideTooltip());
        });
    }

    showTooltip(e) {
        const data = JSON.parse(e.target.getAttribute('data-tooltip-content'));
        const tooltip = document.createElement('div');
        tooltip.className = 'dot-tooltip';
        tooltip.setAttribute('role', 'tooltip');
        
        tooltip.innerHTML = `
            <div class="tooltip-title">${data.title}</div>
            <div class="tooltip-summary">${data.summary}</div>
            <div class="tooltip-footer">
                <div class="tooltip-match">${data.match}% match</div>
                <div class="tooltip-tags">
                    ${data.tags.map(tag => `<span class="tooltip-tag">${tag}</span>`).join('')}
                </div>
            </div>`;

        let x = e.pageX;
        let y = e.pageY;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const tooltipWidth = 280;
        const tooltipHeight = 140;
        const padding = 12;

        // Clamp tooltip within viewport
        if (x + tooltipWidth / 2 > viewportWidth - padding) {
            x = viewportWidth - padding - tooltipWidth / 2;
        }
        if (x - tooltipWidth / 2 < padding) {
            x = padding + tooltipWidth / 2;
        }
        if (y - tooltipHeight < padding) {
            y = e.pageY + 20;
        } else {
            y = e.pageY - 10;
        }

        tooltip.style.left = x + 'px';
        tooltip.style.top = y + 'px';
        document.body.appendChild(tooltip);
        this.currentTooltip = tooltip;
        
        setTimeout(() => tooltip.style.opacity = '1', 10);
    }

    hideTooltip() {
        if (this.currentTooltip) {
            this.currentTooltip.remove();
            this.currentTooltip = null;
        }
    }

    loadTwitterWidgets() {
        console.log('loadTwitterWidgets called');
        setTimeout(() => {
            const twitterContainers = this.panelContent.querySelectorAll('.twitter-embed-container');
            if (twitterContainers.length > 0) {
                console.log('Found Twitter containers:', twitterContainers.length);
                console.log('Container HTML:', twitterContainers[0].innerHTML);
                
                // Check if Twitter script is available
                if (typeof window.twttr === 'undefined') {
                    console.log('Twitter script not loaded, attempting to load...');
                    this.loadTwitterScript();
                    return;
                }
                
                console.log('Window twttr:', typeof window.twttr);
                console.log('twttr ready:', typeof window.twttr.ready);
                console.log('twttr widgets:', typeof window.twttr.widgets);
                
                if (window.twttr.widgets) {
                    console.log('Calling twttr.widgets.load...');
                    try {
                        window.twttr.widgets.load(this.panelContent)
                            .then(() => {
                                console.log('Twitter widgets loaded successfully');
                            })
                            .catch(e => {
                                console.error('Twitter widget load error:', e);
                            });
                    } catch (e) {
                        console.error('Twitter widget call error:', e);
                    }
                } else if (window.twttr.ready) {
                    console.log('Twitter script loading, waiting for ready...');
                    window.twttr.ready(() => {
                        if (window.twttr.widgets) {
                            console.log('Twitter ready, loading widgets...');
                            window.twttr.widgets.load(this.panelContent);
                        }
                    });
                } else {
                    console.log('Twitter script not ready, retrying...');
                    setTimeout(() => this.loadTwitterWidgets(), 1000);
                }
            }
        }, 500);
    }

    loadTwitterScript() {
        if (document.getElementById('twitter-wjs')) {
            console.log('Twitter script already exists, waiting...');
            setTimeout(() => this.loadTwitterWidgets(), 1000);
            return;
        }
        
        console.log('Loading Twitter script...');
        const script = document.createElement('script');
        script.id = 'twitter-wjs';
        script.src = 'https://platform.twitter.com/widgets.js';
        script.async = true;
        script.onload = () => {
            console.log('Twitter script loaded, initializing...');
            setTimeout(() => this.loadTwitterWidgets(), 500);
        };
        script.onerror = () => {
            console.error('Failed to load Twitter script');
        };
        document.head.appendChild(script);
    }

    addDotClickListeners() {
        document.querySelectorAll('.dot').forEach(dot => {
            dot.addEventListener('click', (e) => {
                const filename = e.target.getAttribute('data-filename');
                console.log('Dot clicked, filename:', filename);
                this.showContent(filename);
            });
        });
    }
}

console.log('Creating KnowledgeSearch instance...');
const knowledgeSearch = new KnowledgeSearch();
console.log('KnowledgeSearch instance created:', knowledgeSearch);

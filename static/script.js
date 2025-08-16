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

        // Inline tags container below search input (new UX)
        this.inlineTags = document.getElementById('inlineTags');
        this.tagsLabel = document.getElementById('tagsLabel');
        this.inlineTagsWrap = document.getElementById('inlineTagsWrap');
        this.searchBox = this.searchInput ? this.searchInput.closest('.search-box') : null;
        this.tagsVisible = false;

        // Search state
        this.currentQuery = '';
        this.limit = 30;
        this.offset = 0;
        this.sort = 'relevance'; // kept for API compatibility, but no selector now
        this.selectedTags = new Set();
        this.allTags = [];
        
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

        // Show tags under input on focus
        this.searchInput.addEventListener('focus', async () => {
            try {
                this.tagsVisible = true;
                await this.updateInlineTags(this.searchInput.value.trim());
                // Rely on CSS :focus-within to reveal wrapper; no hidden toggles
            } catch (e) { console.warn('Failed to load tags', e); }
        });
        this.searchInput.addEventListener('blur', () => {
            // Delay to allow chip clicks to register
            setTimeout(() => {
                const ae = document.activeElement;
                const insideChips = this.inlineTagsWrap && this.inlineTagsWrap.contains(ae);
                const insideSearch = this.searchBox && this.searchBox.contains(ae);
                if (!insideChips && !insideSearch) this.hideInlineTags();
            }, 120);
        });

        // Click-away: hide tags if clicking outside search area and chips
        document.addEventListener('mousedown', (e) => {
            const inSearch = this.searchBox && this.searchBox.contains(e.target);
            const inChips = this.inlineTagsWrap && this.inlineTagsWrap.contains(e.target);
            if (!inSearch && !inChips) this.hideInlineTags();
        });
        
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
            // Update tags to overall top when cleared
            this.updateInlineTags('').catch(() => {});
            return;
        }
        
        this.status.textContent = 'SEARCHING...';
        this.searchTimeout = setTimeout(() => {
            this.currentQuery = query;
            this.offset = 0; // reset pagination for new query
            // Update tags for this query
            this.updateInlineTags(query).catch(() => {});
            this.performSearch(query, false);
        }, 300);
    }

    async performSearch(query, append = false) {
        try {
            const tagsParam = [...this.selectedTags].join(',');
            const url = `/search?q=${encodeURIComponent(query)}&limit=${this.limit}&offset=${this.offset}&sort=${encodeURIComponent(this.sort)}${tagsParam ? `&tags=${encodeURIComponent(tagsParam)}` : ''}`;
            const response = await fetch(url);
            const payload = await response.json();
            this.displayResults(payload.results || [], query, payload.total || 0, append);
        } catch (error) {
            console.error('Search error:', error);
            this.status.textContent = 'SEARCH ERROR';
        } finally {
            this.status.textContent = '';
        }
    }

    displayResults(results, query, total, append = false) {
        console.log('Displaying results:', results.length, 'total:', total);
        
        if (!results.length) {
            this.results.innerHTML = `
                <div class="no-results">
                    <h3>NO RESULTS FOUND</h3>
                    <p>Try different search terms or verify your knowledge base</p>
                </div>`;
            if (this.toolbar) this.toolbar.hidden = true;
            return;
        }

        // Inline tags remain as global set; no per-result rebuild required

        const dotsHtml = `
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
                             style="width:${size}px;height:${size}px;background:${this.getIntellectualColor(result.similarity)};animation-delay:${delay}s"
                             data-tooltip-content='{"title":"${this.escapeHtml(result.title)}","summary":"${summary}","match":"${matchPercent}","tags":${JSON.stringify(tags)}}'>
                        </div>`;
                }).join('')}
            </div>`;

        const canShowMore = total > (this.offset + results.length);
        const more = canShowMore ? 
            `<div style="text-align:center;margin-top:16px;">
                <button id="showMore" class="close-panel" style="font-size:14px">Show more</button>
             </div>` : '';

        // No toolbar now

        if (append && this.results.querySelector('.dots-grid')) {
            this.results.querySelector('.dots-grid').insertAdjacentHTML('beforeend', dotsHtml.replace('<div class="dots-grid">','').replace('</div>',''));
            // Update Show more area
            const moreContainer = this.results.querySelector('#showMore')?.parentElement?.parentElement;
            if (moreContainer) moreContainer.remove();
            if (canShowMore) this.results.insertAdjacentHTML('beforeend', more);
        } else {
            this.results.innerHTML = dotsHtml + more;
        }
        this.addTooltipListeners();
        this.addDotClickListeners();
        
        const btn = document.getElementById('showMore');
        if (btn) {
            btn.addEventListener('click', () => {
                // Increment offset and fetch next page, appending
                this.offset += this.limit;
                this.performSearch(this.currentQuery, true);
            });
        }
        
        console.log('Results displayed, dots created:', document.querySelectorAll('.dot').length);
    }

    renderInlineTags(allTags) {
        if (!this.inlineTags) return;
        if (!allTags.length || !this.tagsVisible) {
            this.inlineTags.innerHTML = '';
            return;
        }
        const next = this.normalizeTags(allTags).slice(0, 5);
        // Collect current tags from DOM
        const currentBtns = Array.from(this.inlineTags.querySelectorAll('.chip'));
        const current = currentBtns.map(b => b.getAttribute('data-tag'));

        const toRemove = current.filter(t => !next.includes(t));
        const toAdd = next.filter(t => !current.includes(t));
        const toUpdate = next.filter(t => current.includes(t));

        // Remove with exit animation
        currentBtns.forEach(btn => {
            const t = btn.getAttribute('data-tag');
            const shouldRemove = toRemove.includes(t);
            const isActive = this.selectedTags.has(t);
            if (shouldRemove) {
                btn.classList.add('chip-exit');
                btn.addEventListener('animationend', () => btn.remove(), { once: true });
            } else {
                // Sync active class for kept items
                btn.classList.toggle('active', isActive);
            }
        });

        // Insert additions in next order
        toAdd.forEach(tag => {
            const btn = document.createElement('button');
            btn.className = 'chip chip-enter' + (this.selectedTags.has(tag) ? ' active' : '');
            btn.setAttribute('data-tag', tag);
            btn.textContent = tag;
            btn.addEventListener('animationend', () => btn.classList.remove('chip-enter'), { once: true });
            btn.addEventListener('click', () => {
                if (this.selectedTags.has(tag)) this.selectedTags.delete(tag);
                else this.selectedTags.add(tag);
                // Reset pagination when filters change
                this.offset = 0;
                if (!this.currentQuery) this.currentQuery = this.searchInput.value.trim();
                this.performSearch(this.currentQuery, false);
                // Refresh chip states
                this.renderInlineTags(this.allTags);
            });
            this.inlineTags.appendChild(btn);
        });

        // Reorder to match `next`
        const finalOrder = new Map();
        Array.from(this.inlineTags.querySelectorAll('.chip')).forEach(btn => {
            finalOrder.set(btn.getAttribute('data-tag'), btn);
        });
        next.forEach(tag => {
            const node = finalOrder.get(tag);
            if (node) this.inlineTags.appendChild(node);
        });

        // Visibility handled by CSS focus-within; no hidden toggles here
    }

    async updateInlineTags(query) {
        const q = (query || '').trim();
        const url = q ? `/tags?q=${encodeURIComponent(q)}&limit=5` : `/tags?limit=5`;
        const resp = await fetch(url);
        const data = await resp.json();
        // Normalize to string tags array
        this.allTags = this.normalizeTags(data.map(x => typeof x === 'string' ? x : (x.tag || '')));
        this.renderInlineTags(this.allTags);
    }

    normalizeTags(list) {
        const set = new Set();
        for (const raw of list || []) {
            const t = String(raw || '').trim().toLowerCase();
            if (!t) continue;
            if (!set.has(t)) set.add(t);
        }
        return Array.from(set);
    }

    hideInlineTags() {
        this.tagsVisible = false;
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

    getIntellectualColor(similarity) {
        // Sophisticated, muted palette for intellectual/literary feel
        // Using earthier, more contemplative tones
        const baseColors = [
            { h: 210, s: 15, l: 25 }, // Muted blue-gray
            { h: 45, s: 18, l: 28 },  // Warm brown-gray  
            { h: 160, s: 12, l: 30 }, // Sage green-gray
            { h: 25, s: 20, l: 32 },  // Warm sepia
            { h: 280, s: 8, l: 26 }   // Cool purple-gray
        ];
        
        // Map similarity to color intensity and selection
        const scaledSimilarity = Math.max(0, Math.min(1, similarity));
        const colorIndex = Math.floor(scaledSimilarity * baseColors.length);
        const color = baseColors[Math.min(colorIndex, baseColors.length - 1)];
        
        // Adjust lightness based on similarity (higher similarity = slightly lighter)
        const adjustedLightness = color.l + (scaledSimilarity * 8);
        
        return `hsl(${color.h}, ${color.s}%, ${adjustedLightness}%)`;
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

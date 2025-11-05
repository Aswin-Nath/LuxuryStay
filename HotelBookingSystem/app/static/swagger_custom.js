(function(){
    // inject style
    try{
        const style = document.createElement('style');
        style.innerHTML = `#tag-filter-container { position:fixed; top:12px; right:12px; z-index:2147483647; background:#fff; border:1px solid #ddd; padding:6px; border-radius:6px; box-shadow:0 2px 6px rgba(0,0,0,0.12); font-family: sans-serif; } #tag-filter-select { min-width:220px; }`;
        document.head.appendChild(style);
    }catch(e){ console.warn('failed to inject style for tag dropdown', e); }

    function extractTagFromOpblock(opblock){
        // Try several selectors to find the tag label inside an opblock
        const candidates = [
            '.opblock-summary-tag',
            '.opblock-tag',
            '.opblock-summary .opblock-tag',
            '.opblock-summary > .opblock-tag',
            '[data-tag]'
        ];
        for(const sel of candidates){
            const el = opblock.querySelector(sel);
            if(el && el.textContent && el.textContent.trim()) return el.textContent.trim();
        }
        // fallback to data attribute on the opblock itself
        if(opblock.getAttribute && opblock.getAttribute('data-tag')) return opblock.getAttribute('data-tag').trim();
        return '';
    }

    function collectTags(){
        const opblocks = Array.from(document.querySelectorAll('.opblock'));
        const set = new Set();
        opblocks.forEach(ob=>{
            const t = extractTagFromOpblock(ob);
            if(t) set.add(t);
        });
        return Array.from(set);
    }

    function buildDropdown(){
        const tags = collectTags();
        if(!tags.length){
            console.debug('tag-dropdown: no tags found yet');
            return false;
        }

        let container = document.getElementById('tag-filter-container');
        if(!container){
            container = document.createElement('div');
            container.id = 'tag-filter-container';
            container.setAttribute('aria-hidden','false');
            document.body.appendChild(container);
        }

        if(document.getElementById('tag-filter-select')) return true;

        const sel = document.createElement('select');
        sel.id = 'tag-filter-select';
        sel.setAttribute('aria-label', 'Filter API endpoints by tag');
        const allOpt = document.createElement('option'); allOpt.value = ''; allOpt.text = '-- Show all tags --'; sel.appendChild(allOpt);
        tags.sort().forEach(t=>{ const o=document.createElement('option'); o.value=t; o.text=t; sel.appendChild(o); });

        container.appendChild(sel);
        sel.addEventListener('change', function(){ filterByTag(this.value); });
        console.info('tag-dropdown: built with tags', tags);
        return true;
    }

    function filterByTag(tag){
        const blocks = document.querySelectorAll('.opblock');
        blocks.forEach(b=>{
            const t = extractTagFromOpblock(b) || '';
            if(!tag || t === tag) {
                b.style.display = '';
            } else {
                b.style.display = 'none';
            }
        });
    }

    // Try immediate build (in case script loads after swagger)
    try{ if(buildDropdown()) return; }catch(e){ console.warn('initial tag build failed', e); }

    // Fallback: observe DOM for opblock insertions and build when present
    const observer = new MutationObserver((mutations, obs)=>{
        for(const m of mutations){
            if(m.addedNodes && m.addedNodes.length){
                for(const n of m.addedNodes){
                    try{
                        if(n.nodeType===1 && (n.classList.contains('opblock') || n.querySelector && n.querySelector('.opblock'))){
                            if(buildDropdown()){ obs.disconnect(); return; }
                        }
                    }catch(e){ /* ignore */ }
                }
            }
        }
    });

    // Start observing body for changes; reasonable timeout to stop observing
    try{
        observer.observe(document.body, { childList: true, subtree: true });
    }catch(e){ console.warn('tag-dropdown: observer failed to start', e); }

    // Also keep a polling fallback in case MutationObserver is not allowed
    let attempts = 0;
    const maxAttempts = 150; // ~30s
    const waiter = setInterval(()=>{
        try{
            if(buildDropdown() || attempts > maxAttempts){
                clearInterval(waiter);
                try{ observer.disconnect(); }catch(e){}
            }
        }catch(e){ console.error('tag-dropdown build failed', e); }
        attempts++;
    }, 200);
})();

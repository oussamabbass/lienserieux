document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-avatar] img').forEach((image) => {
        image.addEventListener('error', () => {
            image.hidden = true;
            const fallback = image.parentElement?.querySelector('[class*="__fallback"]');
            if (fallback) fallback.hidden = false;
        }, { once: true });
    });

    const searchInput = document.getElementById('profileSearch');
    const profileCards = [...document.querySelectorAll('.profile-card[data-search]')];
    const noResults = document.getElementById('profileNoResults');
    const profileCount = document.getElementById('profileCount');
    const photoFilter = document.getElementById('profileHasPhoto');
    const bioFilter = document.getElementById('profileHasBio');
    const resetFilters = document.getElementById('profileFiltersReset');

    const normalize = (value) => value
        .toLocaleLowerCase('fr')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');

    if (searchInput && profileCards.length > 0) {
        const updateProfiles = () => {
            const query = normalize(searchInput.value.trim());
            let visibleCount = 0;

            profileCards.forEach((card) => {
                const matchesSearch = normalize(card.dataset.search || '').includes(query);
                const matchesPhoto = !photoFilter?.checked || card.dataset.hasPhoto === 'true';
                const matchesBio = !bioFilter?.checked || card.dataset.hasBio === 'true';
                const isMatch = matchesSearch && matchesPhoto && matchesBio;
                card.hidden = !isMatch;
                if (isMatch) visibleCount += 1;
            });

            if (noResults) noResults.hidden = visibleCount > 0;
            if (profileCount) {
                profileCount.textContent = `${visibleCount} profil${visibleCount > 1 ? 's' : ''}`;
            }
        };

        searchInput.addEventListener('input', updateProfiles);
        photoFilter?.addEventListener('change', updateProfiles);
        bioFilter?.addEventListener('change', updateProfiles);
        resetFilters?.addEventListener('click', () => {
            searchInput.value = '';
            if (photoFilter) photoFilter.checked = false;
            if (bioFilter) bioFilter.checked = false;
            updateProfiles();
            searchInput.focus();
        });
    }

    const conversationSearch = document.getElementById('conversationSearch');
    const conversations = [...document.querySelectorAll('.conversation-list__item[data-search]')];
    const noConversationResults = document.getElementById('conversationNoResults');

    conversationSearch?.addEventListener('input', () => {
        const query = normalize(conversationSearch.value.trim());
        let visibleCount = 0;
        conversations.forEach((item) => {
            const isMatch = normalize(item.dataset.search || '').includes(query);
            item.hidden = !isMatch;
            if (isMatch) visibleCount += 1;
        });
        if (noConversationResults) noConversationResults.hidden = visibleCount > 0;
    });
});

/* Effet 3D holographique sur chaque clic */
document.addEventListener('click', (e) => {
    const burst = document.createElement('div');
    burst.className = 'holographic-burst';
    burst.style.left = e.clientX + 'px';
    burst.style.top = e.clientY + 'px';
    document.body.appendChild(burst);
    burst.addEventListener('animationend', () => burst.remove());
}, { passive: true });

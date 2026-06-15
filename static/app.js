// Поиск
document.getElementById('searchInput')?.addEventListener('input', function(e) {
    const term = e.target.value.toLowerCase();
    document.querySelectorAll('.card').forEach(card => {
        const title = card.querySelector('h3')?.textContent.toLowerCase() || '';
        card.style.display = title.includes(term) ? '' : 'none';
    });
});

// Копирование
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        const notif = document.createElement('div');
        notif.textContent = '✅ Скопировано!';
        notif.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#10b981;color:white;padding:12px 24px;border-radius:9999px;font-weight:500;';
        document.body.appendChild(notif);
        setTimeout(() => notif.remove(), 2000);
    });
}

// Анимация при загрузке
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.card').forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        setTimeout(() => {
            card.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            card.style.transitionDelay = (i * 50) + 'ms';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100);
    });
});

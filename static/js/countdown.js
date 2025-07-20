function startCountdownToMidnight(display) {
    function updateCountdown() {
        const now = new Date();
        const midnight = new Date();
        midnight.setHours(24, 0, 0, 0); // Next midnight
        
        const timeDiff = midnight.getTime() - now.getTime();
        
        if (timeDiff <= 0) {
            display.textContent = "Tempo restante: 00h 00m 00s";
            return;
        }
        
        const hours = Math.floor(timeDiff / (1000 * 60 * 60));
        const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((timeDiff % (1000 * 60)) / 1000);
        
        const hoursStr = hours < 10 ? "0" + hours : hours;
        const minutesStr = minutes < 10 ? "0" + minutes : minutes;
        const secondsStr = seconds < 10 ? "0" + seconds : seconds;
        
        display.textContent = `Tempo restante: ${hoursStr}h ${minutesStr}m ${secondsStr}s`;
    }
    
    updateCountdown(); // Update immediately
    setInterval(updateCountdown, 1000); // Update every second
}

function getNextDay() {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.getDate().toString().padStart(2, '0');
}

window.onload = function () {
    const countdownElement = document.getElementById('countdown');
    if (countdownElement) {
        startCountdownToMidnight(countdownElement);
    }

    const nextDay = getNextDay();
    const newsDescription = document.getElementById('newsDescription');
    if (newsDescription) {
        newsDescription.innerHTML = `<strong>Novas regras do Pix</strong>, válidas a partir de <strong>05/03/2025</strong>, determinarão o <strong>bloqueio de chaves</strong> vinculadas a CPFs com pendências na Receita Federal. <strong>Mais de 8 milhões de chaves</strong> serão bloqueadas até <strong>${nextDay}/03/25</strong> se as irregularidades não forem resolvidas, <strong>impedindo o envio e recebimento de valores pelo Pix</strong>.`;
    }
};
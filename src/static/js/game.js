const tg = window.Telegram.WebApp;
tg.expand();

let isAnswered = false;

async function loadQuestion() {
    isAnswered = false;
    document.getElementById('loading').style.display = 'block';
    document.getElementById('game-container').style.display = 'none';
    document.getElementById('feedback').style.display = 'none';
    document.getElementById('next-btn').style.display = 'none';
    document.getElementById('options-container').innerHTML = '';

    try {
        const response = await fetch('/api/get_question');
        const data = await response.json();

        if (data.error) {
            alert('Ошибка: ' + data.error);
            return;
        }

        const audioPlayer = document.getElementById('audio-player');
        audioPlayer.src = data.voice_url;

        const optionsContainer = document.getElementById('options-container');

        data.options.forEach(option => {
            const card = document.createElement('div');
            card.className = 'option-card';
            card.onclick = () => checkAnswer(option, card);

            const img = document.createElement('img');
            img.src = option.image_url || 'https://via.placeholder.com/150?text=No+Image'; // Fallback
            img.className = 'option-image';

            const name = document.createElement('div');
            name.className = 'option-name';
            name.innerText = option.name;

            card.appendChild(img);
            card.appendChild(name);
            optionsContainer.appendChild(card);
        });

        document.getElementById('loading').style.display = 'none';
        document.getElementById('game-container').style.display = 'flex';

    } catch (e) {
        console.error(e);
        alert('Произошла ошибка при загрузке данных.');
    }
}

function checkAnswer(option, cardElement) {
    if (isAnswered) return;
    isAnswered = true;

    const feedback = document.getElementById('feedback');
    const nextBtn = document.getElementById('next-btn');

    if (option.is_correct) {
        feedback.innerText = "Верно! 🎉";
        feedback.className = 'feedback success';
        cardElement.style.border = "3px solid #28a745";
        launchConfetti();
        tg.HapticFeedback.notificationOccurred('success');
    } else {
        feedback.innerText = `Увы, неверно 🤷‍♂️`;
        feedback.className = 'feedback error';
        cardElement.style.border = "3px solid #dc3545";
        launchCross(cardElement);
        tg.HapticFeedback.notificationOccurred('error');
    }

    feedback.style.display = 'block';
    nextBtn.style.display = 'block';
}

function launchCross(cardElement) {
    const cross = document.createElement('div');
    cross.className = 'cross-icon';
    cross.innerText = '❌';
    cardElement.appendChild(cross);
    setTimeout(() => cross.remove(), 800);
}

function launchConfetti() {
    for (let i = 0; i < 50; i++) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        confetti.style.left = Math.random() * 100 + 'vw';
        confetti.style.backgroundColor = `hsl(${Math.random() * 360}, 100%, 50%)`;
        confetti.style.animationDuration = (Math.random() * 2 + 1) + 's';
        document.body.appendChild(confetti);
        setTimeout(() => confetti.remove(), 3000);
    }
}

// Load first question on start
loadQuestion();

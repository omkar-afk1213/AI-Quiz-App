document.addEventListener('DOMContentLoaded', function () {
  const timerBadge = document.getElementById('timerBadge');
  const progressBar = document.getElementById('progressBar');
  const form = document.getElementById('quizForm');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const questionBlocks = Array.from(document.querySelectorAll('.question-block'));

  if (!timerBadge || !form) return;

  let timeLeft = 60;
  const countdown = setInterval(() => {
    timeLeft -= 1;
    timerBadge.textContent = `${timeLeft}s`;
    if (timeLeft <= 10) {
      timerBadge.classList.add('bg-warning');
      timerBadge.classList.remove('bg-danger');
    }
    if (timeLeft <= 0) {
      clearInterval(countdown);
      form.submit();
    }
  }, 1000);

  function showQuestion(index) {
    if (!questionBlocks.length) return;

    questionBlocks.forEach((block, blockIndex) => {
      const isVisible = blockIndex === index;
      block.classList.toggle('d-none', !isVisible);
    });

    const currentQuestion = index + 1;
    const total = questionBlocks.length;
    if (progressBar) {
      progressBar.style.width = `${(currentQuestion / total) * 100}%`;
    }

    if (prevBtn) {
      prevBtn.style.display = index === 0 ? 'none' : 'inline-block';
    }

    if (nextBtn) {
      const isLastQuestion = index === total - 1;
      nextBtn.textContent = isLastQuestion ? 'Submit Quiz' : 'Next Question';
      nextBtn.type = isLastQuestion ? 'submit' : 'button';
    }
  }

  let currentIndex = 0;
  if (window.quizState && typeof window.quizState.currentIndex === 'number') {
    currentIndex = window.quizState.currentIndex;
  }

  showQuestion(currentIndex);

  if (prevBtn) {
    prevBtn.addEventListener('click', function () {
      if (currentIndex > 0) {
        currentIndex -= 1;
        showQuestion(currentIndex);
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', function (event) {
      const activeBlock = questionBlocks[currentIndex];
      const checkedOption = activeBlock ? activeBlock.querySelector('input[type="radio"]:checked') : null;

      if (!checkedOption) {
        event.preventDefault();
        alert('Please select an answer before moving to the next question.');
        return;
      }

      if (currentIndex < questionBlocks.length - 1) {
        event.preventDefault();
        currentIndex += 1;
        showQuestion(currentIndex);
      }
    });
  }

  form.addEventListener('submit', function (event) {
    const allAnswered = questionBlocks.every((block) => block.querySelector('input[type="radio"]:checked'));
    if (!allAnswered) {
      event.preventDefault();
      alert('Please answer all questions before submitting the quiz.');
    }
  });
});

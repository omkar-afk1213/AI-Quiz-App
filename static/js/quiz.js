document.addEventListener('DOMContentLoaded', function () {
  const timerBadge = document.getElementById('timerBadge');
  const progressBar = document.getElementById('progressBar');
  const form = document.getElementById('quizForm');

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

  if (progressBar) {
    const questionBlocks = document.querySelectorAll('.question-block');
    const currentBlock = questionBlocks.length ? questionBlocks[0] : null;
    if (currentBlock) {
      const total = questionBlocks.length;
      const questionNumber = parseInt(currentBlock.dataset.index || 0, 10) + 1;
      progressBar.style.width = `${(questionNumber / total) * 100}%`;
    }
  }
});

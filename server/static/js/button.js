document.getElementById('logoutButton').addEventListener('click', function (event) {
    event.preventDefault(); // предотвращаем переход по ссылке, если это нужно

    fetch('/logout', { // замените '/logout' на нужный вам URL
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            // добавьте другие заголовки, если необходимо
        },
        body: JSON.stringify({}) // добавьте данные, если нужно
    })
        .then(response => {
            if (response.ok) {
                // Обработка успешного ответа
                console.log('Вы вышли успешно');
                // Например, перенаправление на главную страницу
                window.location.href = '/'; // замените на нужный URL
            } else {
                // Обработка ошибки
                console.error('Ошибка при выходе');
            }
        })
        .catch(error => {
            console.error('Ошибка сети:', error);
        });
});
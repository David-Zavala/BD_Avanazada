const navbarItems = document.querySelectorAll('.navbar ul li');

navbarItems.forEach(item => {
  item.addEventListener('click', () => {
    navbarItems.forEach(item => item.classList.remove('active'));
    item.classList.add('active');
  });
});

let username = 'usuario'; // Cambiar por el nombre del usuario activo

let loginButton = document.getElementById('login-button');
let userContainer = document.getElementById('user-container');

loginButton.addEventListener('click', () => {
  userContainer.innerHTML = `<p>Bienvenido, ${username}</p>`;
});

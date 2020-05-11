const backdropEl = document.getElementById('backdrop-main');
const menuShowBtnEl = document.getElementById('menu-show-btn');
const menuHideBtnEl = menuShowBtnEl.nextElementSibling;
const sideBar = document.querySelector('.sidebar');

const menuBtnClickHandler = function () {
  backdropEl.classList.toggle('invisible');
  menuShowBtnEl.classList.toggle('invisible');
  menuHideBtnEl.classList.toggle('invisible');
  sideBar.classList.toggle('invisible');
};

menuShowBtnEl.onclick = menuBtnClickHandler;
menuHideBtnEl.onclick = menuBtnClickHandler;

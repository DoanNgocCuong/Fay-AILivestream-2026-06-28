// Định nghĩa biến
const slideDistance = 500;
let currentTranslate = 0;
let menu, prevButton, nextButton;

function updateButtons() {
    if (!prevButton || !nextButton || !menu) return;
    prevButton.disabled = currentTranslate === 0;
    nextButton.disabled = currentTranslate <= -(menu.scrollWidth - menu.clientWidth);
}

function initializeSlider() {
    // Lấy phần tử DOM
    menu = document.querySelector('.menu');
    prevButton = document.getElementById('prevButton');
    nextButton = document.getElementById('nextButton');
    
    // Đảm bảo tất cả phần tử tồn tại
    if (!menu || !prevButton || !nextButton) return;
    
    // Thêm event listener
    prevButton.addEventListener('click', () => {
        if (menu.scrollWidth > menu.clientWidth) { 
            currentTranslate = Math.min(currentTranslate + slideDistance, 0); 
            menu.style.transform = `translateX(${currentTranslate}px)`;
            updateButtons();
        }
    });
    
    nextButton.addEventListener('click', () => {
        if (menu.scrollWidth > menu.clientWidth) { 
            currentTranslate = Math.max(currentTranslate - slideDistance, -(menu.scrollWidth - menu.clientWidth)); 
            menu.style.transform = `translateX(${currentTranslate}px)`;
            updateButtons();
        }
    });
    
    // Khởi tạo trạng thái nút
    updateButtons();
}

// Khởi tạo sau khi DOM tải xong
document.addEventListener('DOMContentLoaded', initializeSlider);

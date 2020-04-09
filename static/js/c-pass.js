function check(input) {
    if (input.value != document.getElementById('pw').value) {
        input.setCustomValidity('Password do not match');
    } else {
        input.setCustomValidity('');
    }
}
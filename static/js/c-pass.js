function check(input) {
    if (input.value != document.getElementById('pw').value) {
        input.setCustomValidity('Passwords do not match');
    } else {
        input.setCustomValidity('');
    }
}
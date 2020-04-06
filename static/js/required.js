function change_required(selection) {
    var snum = document.getElementById("snum");
    if (selection.checked && selection.id == "instructor-acc") {
        snum.removeAttribute("required");
    } else {
        snum.setAttribute("required", "true");
    }
}
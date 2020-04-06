window.onscroll = function() {fixedHeader()};

var header = document.getElementById("fixed-header");
var fix = header.offsetTop;

function fixedHeader() {
  if (window.pageYOffset > fix) {
    header.classList.add("fix");
  } else {
    header.classList.remove("fix");
  }
}
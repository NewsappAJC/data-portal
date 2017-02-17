window.onload = function() {
  var a = window.location.href.split('/');
  var rel = a[a.length-2]; // Get just the relative link
  if (rel !== 'search') rel = 'upload';

  $('.nav-tab').each(function() {
    if (this.dataset.href === rel) {
      $(this).addClass('active');
    }
    else {
      $(this).removeClass('active');
    };
  });
}

'use strict';

window.onload = function() {
  function getURL() {
    $.ajax({
      url: '/search/get-presigned-url/',
      type: 'GET',
      success: function(res) {
        window.location.href = res.url;
      },
      error: function(e) {
        console.log(e);
      }
    });
  };
  function main() {
    // DOM refs
    var $urlButtons = $('.url-btn');

    $urlButtons.on('click', function() {
      getURL();
    })
    $('#search-submit, #detail-submit').on('click', function() {
      $(this).button('loading');
      $('#search-error').html('');
    })
  }
  main();
};

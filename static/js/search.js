'use strict';

window.onload = function() {
  function getCSV() {
    window.location.href='/search/get-all-results/';
  };
  function main() {
    // DOM refs
    var $urlButtons = $('.url-btn');

    $urlButtons.on('click', function() {
      $(this).button('loading')
      getCSV();
    })
    $('#search-submit, #detail-submit').on('click', function() {
      $(this).button('loading');
      $('#search-error').html('');
    })
  }
  main();
};

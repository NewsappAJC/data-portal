'use strict';

window.onload = function() {
  // DOM refs
  var $downloadButton = $('#download-btn');

  function getCSV() {
    window.location.href='/search/get-all-results/';
  };

  function main() {
    $downloadButton.on('click', function() {
      $(this).button('loading');
      getCSV();
    })
    $('#search-submit, #detail-submit').on('click', function() {
      $(this).button('loading');
      $('#search-error').html('');
    })
  }

  main();
};

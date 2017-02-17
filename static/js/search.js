'use strict';

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
  $('#toggle-filters').on('click', function() {
    $('#search-filters').toggle();
    $('#hide').toggle();
    $('#show').toggle();
  })
  $('#search-submit, #detail-submit').on('click', function() {
    $(this).button('loading');
    $('#search-error').html('');
  })
}

main();

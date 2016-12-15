'use strict';

window.onload = function() {
  function getURL(id) {
    $.ajax({
      url: '/get-presigned-url/' + id + '/',
      type: 'GET',
      success: function(res) {
        window.location.href = res;
      },
      error: function(e) {
        console.log(e);
      }
    });
  };
  function main() {
    // DOM refs
    var urlButtons = $('.url-btn');

    urlButtons.on('click', function() {
      var id = this.dataset.id;
      getURL(id);
    })
  }
};

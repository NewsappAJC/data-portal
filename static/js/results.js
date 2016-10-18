var c = 0;

function getResult(cb) {
  $.ajax({
    type: 'GET', 
    url: '/check-status/',
    success: function(res) {
      c++;
      if (cb(res) == 'PENDING') {
        if (c < 10) {
          setTimeout(getResult(checkResponseStatus), 500)
        }
      }
    },
    error: function(res) {
      console.log('request failed')
    }
  });
};

function checkResponseStatus(res) {
    console.log(res)
    if (res.status == 'PENDING') {
      return 'PENDING';
    }
    else if (res.status === 'SUCCESS') {
      $('#response').html('SUCCESS');
      $('#response').css('color', 'green');
      generateTable(res.result);
      return;
    }
    else {
      $('#response').html('FAILURE');
      $('#details').html(res.result)
      return;
    }
}

function generateTable(data) {
  var rows = data.map(function(row, i) {
    var cells = row.map(function(cell) {
      if (i === 0) {
        return `<th>${cell}</th>`
      }
      else {
        return `<td>${cell}</td>`
      };
    });

    return `<tr>${cells.join('')}</tr>`
  });

  var markup = `
    <table>
      ${rows.join('')}
    </table>
  `;

  $('#details').html(markup)
}

getResult(checkResponseStatus);

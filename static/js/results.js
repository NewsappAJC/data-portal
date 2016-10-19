// DOM refs
var c = 0;

function getResult(cb) {
  $.ajax({
    type: 'GET', 
    url: '/check-status/',
    success: function(res) {
      c++;
      if (cb(res) == 'incomplete') {
        if (c < 50) {
          console.log('trying...')
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
      return 'incomplete';
    }
    else if (res.status === 'SUCCESS') {
      $('#progress-bar').css('width', '100%')
      $('#response').html('SUCCESS');
      $('#response').css('color', 'green');
      generateTable(res.result);
      return;
    }
    else if (res.status === 'PROGRESS') {
      $('#progress-bar').css('width', (100 * res.result.current / res.result.total) + '%')
      return 'incomplete'
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

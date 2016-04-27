if ($('#hive').length) {
  var hive = new Snap('#hive');
  var img_width = $('#hive').width();
  var left_pos = img_width * .5;

  var pixelated = hive.path("M12.4,20.3v31.8l28,15.8l28-15.8V20.3l-28-15.8L12.4,20.3z M39.2,56.4l-16.3-9V27.9l16.3,9.3L39.2,56.4z M57.7,47.4l-16.1,9l0-19.2l16.1-9.4V47.4z M57.7,25.2L40.4,35.5L22.9,25.2l17.5-9.4L57.7,25.2z").transform("translate(319, 50)").attr("fill", "#908e8e");
  var all = hive.group().transform("matrix(2, 0, 0, 2, -100, -100)");

  var height = 50;
  var width = 58;
  var rows = (($(window).height() / height) / 2) + 1;
  var cols = (($(window).width() / width) / 2) + 1;


  for (var j = 0; j < rows; j++) {
    for (var i = 0; i < cols; i++) {
      x = i * width + (j%2*width/2);
      y = j * height;
      all.add(pixelated.clone().transform("translate("+x+","+y+")"));
    }
  }

  all.add(pixelated);

  var brightenLogo = function () {
    var glowPosition = Math.floor(Math.random()*rows*cols);

    all[glowPosition].animate({fill: "#FFF"}, 1000, function() {
      darkenLogo(all[glowPosition]);
    });
  };

  var darkenLogo = function (el) {
    el.animate({fill: "#908e8e"}, 1000, brightenLogo);
  };

  brightenLogo();

}

$(function () {
  var handler = setInterval(function () {
    $.ajax({
      method: 'GET',
      url: '/'
    }).success(function (data) {
      if (/Pixelated Mail/g.test(data)) {
        window.location="/";
      }
    });
  }, 2000);

  $('#hive-section').height($(window).height());

  $(window).resize(function() {
    window.location.reload(true);
  });
});

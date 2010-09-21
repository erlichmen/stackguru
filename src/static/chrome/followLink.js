$(function() {
  var questionId = null;
  getQuestionId = function() {
	if (questionId == null) {
		questionId = $(".vote input[type=hidden]:first").val();
	}
	
	return questionId;
  }
  
  baseUrl = function() {
  	return '{{domain}}/follow/';
  }
  
  baseUnfollowUrl = function() {
  	return '{{domain}}/unfollow/';
  }
      
  function addParams(url) {
	url += "?domain=" + window.location.host;
	url += "&token=" + '{{ token }}';
	return url;  
  }
  
  updateAttributes = function(link, isFollowing) {
	getTitle = function() {
		if (isFollowing) {
			return "stop notifications from stackguru about this question";
		} else {
			return "get notifications from stackguru about this question";
		}
	}
	
	getText = function() {
		if (isFollowing) {
			return "unfollow"
		} else {
			return "follow"
		}
	}
  
  	getUrl = function() {
  		if (isFollowing) {
  			return baseUnfollowUrl() + getQuestionId();
  		} else {
  			return baseUrl() + getQuestionId();
  		}
  	}
  	
  	link.data("follow", isFollowing);
  	return link.attr({'href': getUrl(), 'title': getTitle()}).text(getText());
  } 
  
  createFollowLink = function(isFollowing) {
	
	follow = function() {
		$this = $(this)
		url = addParams($this.attr("href"));
		$.getJSON(url, function(data) {
			alert(data.msg);
			if (data.status == "success") {
				updateAttributes($this, !$this.data("follow"));
			}				
		});
		
		return false;   
	}  
	
	sep = $("<span></span>").addClass('lsep').text("|"); 
	a = updateAttributes($("<a></a>"), isFollowing);
	a.click(follow);
	menu = $(".post-menu:first");
	sep.appendTo(menu);
	a.appendTo(menu);  
  }
  
  initLink = function() {
	getIsFollowing = function(data) {
		for (index in data.ids) {
			if (data.ids[index] == getQuestionId()) {
				return true;
			} 
		}
		
		return false;
	}
  	
  	followingLink = addParams(baseUrl());
  	$.getJSON(followingLink, function(data) {
  		createFollowLink(getIsFollowing(data));
	});
  };
  initLink();  
});
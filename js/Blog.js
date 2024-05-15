
window.onload =function () {
	// 左侧菜单栏
	var tabLi=document.getElementById("tab_id").getElementsByTagName("li");
	var articalLi=document.getElementById("artical_det").getElementsByTagName("div");
	for (var i = 0; i <tabLi.length ; i++) {
		tabLi[i].index = i;
		tabLi[i].onmouseover = function(){
			for (var n = 0; n < tabLi.length; n++) {
				tabLi[n].className="";
			};
			this.className="tab_1";
			for (var n = 0; n < articalLi.length; n++) {
				articalLi[n].style.display="none";
			};
			articalLi[this.index].style.display="block";
		}
	};

//=====================登陆注册页面动态切换
	var lgLi=document.getElementById("lgmain").getElementsByTagName("li");
	var showlg_1=document.getElementById("showlg_1");
	var showlg_2=document.getElementById("showlg_2");
	for (var i = 0; i <lgLi.length ; i++) {
		if(i==0){
			lgLi[i].onclick = function(){
			showlg_1.style.display="block";
			showlg_2.style.display="none";
			}
		}else{
			lgLi[i].onclick = function(){
			showlg_2.style.display="block";
			showlg_1.style.display="none";
			}
		}	
	};

	//登陆成功用户页面切换
	var loginspan = document.getElementById('loginspan').innerHTML;
	var loginb = document.getElementById('loginb');
	var logina = document.getElementById('logina');
	if (loginspan!="") {
		logina.style.display = "block";
		loginb.style.display = "none";
	};
}
//AJAX实现导航栏静态切换
function showHint(a) {

	var xmlhttp;
	if (window.XMLHttpRequest)
	  {// code for IE7+, Firefox, Chrome, Opera, Safari
	  xmlhttp=new XMLHttpRequest();
	  }
	else
	  {// code for IE6, IE5
	  xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
	  }
	xmlhttp.onreadystatechange=function()
	  {
	  if (xmlhttp.readyState==4 && xmlhttp.status==200)
	    {
	    document.getElementById("mydiv").innerHTML=xmlhttp.responseText;
	    onload();
	    }
	  }
	if(a==2){
		xmlhttp.open("GET","about.jsp",true);
	}else if(a==3){
		xmlhttp.open("GET","record.jsp",true);	
	}else if(a==4){
		xmlhttp.open("GET","mood.jsp",true);
	}else if(a==5){
		xmlhttp.open("GET","share.jsp",true);
	}else{
		xmlhttp.open("GET","message.jsp",true);
	}
	xmlhttp.send();
}

//登陆与注册模块显示
function login (i) {
	var loginbg = document.getElementById('loginbg');
	var lgmain = document.getElementById('lgmain');
	var showlg_1 = document.getElementById('showlg_1');
	var showlg_2 = document.getElementById('showlg_2');
	loginbg.style.display = "block";
	lgmain.style.display = "block";
	if(i==1){
		showlg_1.style.display = "block";
		showlg_2.style.display = "none";
	}else{
		showlg_1.style.display = "none";
		showlg_2.style.display = "block";
	}
	
}
//登陆与注册模块隐藏
function noshow(argument) {
	var loginbg = document.getElementById('loginbg');
	var lgmain = document.getElementById('lgmain');
	loginbg.style.display = "none";
	lgmain.style.display = "none";
}
const inputbox=document.getElementById("task");
const listcont=document.getElementById("list");
function addtask(){
    if (inputbox.value ===''){
        alert("WRITE SOMETHING IN THE FIELD");
    }
    else{
    let li=document.createElement("li");
    li.innerHTML=inputbox.value;
    listcont.appendChild(li);
    inputbox.value='';
    let span=document.createElement("span");
    span.innerHTML="\u00d7";
    li.appendChild(span);
    savedata();

    }
    

}listcont.addEventListener("click",function(e){
    if(e.target.tagName==="LI"){
        e.target.classList.toggle("checked");
        savedata();

    }else if(e.target.tagName==="SPAN"){
       e.target.parentElement.remove();
       savedata();
     }
},false);

function savedata(){
    localStorage.setItem("data",listcont.innerHTML);
}
function getdata(){
    listcont.innerHTML=localStorage.getItem("data");
}
getdata();


let transactions=[];

let currency="INR";
let symbol="₹";
let rates={INR:1,USD:0.012,EUR:0.011};

/* NAVIGATION */
function go(page){
window.location.href=page;
}

/* ADD TRANSACTION */
function addTransaction(){

let desc=document.getElementById("desc").value;
let amount=parseFloat(document.getElementById("amount").value);
let type=document.getElementById("type").value;

if(!desc || isNaN(amount)) return;

transactions.push({desc,amount,type});
updateUI();
}

/* UI UPDATE */
function updateUI(){

let income=0,expense=0;

transactions.forEach(t=>{
if(t.type==="income") income+=t.amount;
else expense+=t.amount;
});

let balance=income-expense;

if(document.getElementById("balance")){
document.getElementById("balance").innerText=symbol+balance;
document.getElementById("income").innerText="Income "+symbol+income;
document.getElementById("expense").innerText="Expense "+symbol+expense;
}

if(document.getElementById("statsIncome")){
document.getElementById("statsIncome").innerText=symbol+income;
document.getElementById("statsExpense").innerText=symbol+expense;
document.getElementById("statsSavings").innerText=symbol+(income-expense);
}
}

/* CHAT */
function sendMessage(){

let input=document.getElementById("chatInput");
let msg=input.value;

if(!msg) return;

addChat(msg,"user");
addChat("Try to save at least 20% of income","ai");

input.value="";
}

function addChat(text,type){
let div=document.createElement("div");
div.className="chat "+type;
div.innerText=text;
document.getElementById("chatBox").appendChild(div);
}

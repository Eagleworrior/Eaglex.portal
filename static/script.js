// EAGLEX CASINO client

const balanceEl = document.getElementById("balance");
const spinBtn = document.getElementById("spinBtn");
const depositBtn = document.getElementById("depositBtn");
const withdrawBtn = document.getElementById("withdrawBtn");
const betInput = document.getElementById("bet");
const winsList = document.getElementById("wins");
const symbolsContainer = document.getElementById("symbols");
const reelsEls = [
  document.getElementById("reel0"),
  document.getElementById("reel1"),
  document.getElementById("reel2")
];
const symbolsCard = document.getElementById("symbolsCard");
const toggleSymbols = document.getElementById("toggleSymbols");
const minDepositEl = document.getElementById("minDeposit");
const minWithdrawEl = document.getElementById("minWithdraw");

const withdrawModal = document.getElementById("withdrawModal");
const openWithdraw = document.getElementById("openWithdraw");
const closeWithdraw = document.getElementById("closeWithdraw");
const submitWithdraw = document.getElementById("submitWithdraw");
const withdrawMethod = document.getElementById("withdrawMethod");
const withdrawAmount = document.getElementById("withdrawAmount");
const withdrawDetails = document.getElementById("withdrawDetails");
const withdrawMsg = document.getElementById("withdrawMsg");

const modeDemoBtn = document.getElementById("modeDemo");
const modeRealBtn = document.getElementById("modeReal");

let currentMode = "demo";

const SYMBOLS = [
  "🍒","🍋","🍊","🍉","🍇","🍓","🥭","🍍","🍑","🍈",
  "7️⃣","🔔","⭐","💎","💰","🎲","🎰",
  "🚗","🏎️","🚀","🛩️","🚁","🚤",
  "🍔","🍕","🍟","🍩","🍪","🍫","🍦","🍰",
  "👑","🧧","🎁","🪙","📿","🔮",
  "🐶","🐱","🦁","🐯","🦄","🐉",
  "♠️","♥️","♦️","♣️","🃏","🎟️"
];

function populateSymbols(){
  if(!symbolsContainer) return;
  symbolsContainer.innerHTML = "";
  for(let s of SYMBOLS){
    const el = document.createElement("div");
    el.className = "s";
    el.textContent = s;
    symbolsContainer.appendChild(el);
  }
}

async function fetchBalance(){
  if(!balanceEl) return;
  try{
    const res = await fetch("/api/balance");
    const j = await res.json();
    if(j.error){
      balanceEl.textContent = "Login required.";
      return;
    }
    balanceEl.innerHTML =
      `<span class="balance-demo">DEMO: KES ${j.demo_balance.toFixed(2)}</span> ` +
      `<span class="balance-real">REAL: KES ${j.real_balance.toFixed(2)}</span>`;
    if(minDepositEl) minDepositEl.textContent = `KES ${j.min_deposit}`;
    if(minWithdrawEl) minWithdrawEl.textContent = `KES ${j.min_withdraw}`;
    if(betInput) betInput.min = j.min_play;
  }catch(e){
    balanceEl.textContent = "Balance: --";
  }
}

async function fetchSettings(){
  try{
    const res = await fetch("/deposit");
    const j = await res.json();
    const dep = document.getElementById("depositInstructions");
    if(dep && j.instructions){
      dep.querySelector("ol").innerHTML = j.instructions.map((s,i)=>`<li>${s}</li>`).join("");
    }
    const w = await fetch("/api/withdraw_methods");
    const wj = await w.json();
    if(withdrawMethod && wj.methods){
      withdrawMethod.innerHTML = wj.methods.map(m=>`<option value="${m.id}">${m.label}</option>`).join("");
    }
    if(withdrawAmount) withdrawAmount.min = wj.min_withdraw;
  }catch(e){
    console.error(e);
  }
}

function animateReels(visible){
  if(!reelsEls[0]) return;
  for(let i=0;i<3;i++){
    reelsEls[i].innerHTML = "";
    for(let r=0;r<3;r++){
      const d = document.createElement("div");
      d.className = "symbol";
      d.textContent = visible[i][r];
      reelsEls[i].appendChild(d);
    }
  }
}

function setMode(mode){
  currentMode = mode;
  if(!modeDemoBtn || !modeRealBtn) return;
  if(mode === "demo"){
    modeDemoBtn.classList.add("active");
    modeRealBtn.classList.remove("active");
  } else {
    modeRealBtn.classList.add("active");
    modeDemoBtn.classList.remove("active");
  }
}

async function spin(){
  if(!betInput || !spinBtn) return;
  const bet = parseFloat(betInput.value || "0");
  const minBet = parseFloat(betInput.min || "20");
  if(isNaN(bet) || bet < minBet){
    alert(`Minimum bet is KES ${minBet}`);
    return;
  }
  spinBtn.disabled = true;
  spinBtn.textContent = "Spinning...";
  try{
    const res = await fetch("/api/spin", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({bet, mode: currentMode})
    });

    let payload = null;
    try {
      payload = await res.json();
    } catch (e) {
      throw new Error(`Server returned status ${res.status}`);
    }

    if (!res.ok) {
      const serverMsg = payload && payload.error ? payload.error : `Server error ${res.status}`;
      if (res.status === 402 && currentMode === "real") {
        alert(serverMsg + "\n\nOpen deposit instructions now.");
        if(depositBtn) depositBtn.click();
      } else {
        alert(serverMsg);
      }
      return;
    }

    const rounds = 10;
    for(let r=0;r<rounds;r++){
      const temp = [];
      for(let i=0;i<3;i++){
        temp.push([
          SYMBOLS[Math.floor(Math.random()*SYMBOLS.length)],
          SYMBOLS[Math.floor(Math.random()*SYMBOLS.length)],
          SYMBOLS[Math.floor(Math.random()*SYMBOLS.length)]
        ]);
      }
      animateReels(temp);
      await new Promise(res=>setTimeout(res, 50 + r*25));
    }

    animateReels(payload.reels);
    await fetchBalance();
    const modeBadge = payload.mode === "demo" ? " (DEMO)" : " (REAL)";
    if(winsList){
      const li = document.createElement("li");
      if(payload.payout && payload.payout > 0){
        li.textContent = `WIN KES ${payload.payout.toFixed(2)} — ${payload.center.join(" ")}${modeBadge}`;
      } else {
        li.textContent = `Lost KES ${bet.toFixed(2)} — ${payload.center.join(" ")}${modeBadge}`;
      }
      winsList.prepend(li);
    }
  }catch(err){
    console.error("Spin error:", err);
    alert("Spin failed: " + (err.message || "Network or server error"));
  }finally{
    spinBtn.disabled = false;
    spinBtn.textContent = "SPIN";
  }
}

if(depositBtn){
  depositBtn.addEventListener("click", async ()=>{
    const res = await fetch("/deposit");
    const j = await res.json();
    let msg = `${j.title}\n\nMinimum deposit: KES ${j.minimum_deposit}\n\n`;
    msg += j.instructions.map((s,i)=>`${i+1}. ${s}`).join("\n");
    alert(msg);
  });
}

if(toggleSymbols && symbolsCard){
  toggleSymbols.addEventListener("click", ()=>{
    symbolsCard.classList.toggle("collapsed");
    symbolsCard.setAttribute("aria-hidden", symbolsCard.classList.contains("collapsed"));
  });
}

if(openWithdraw && withdrawModal){
  openWithdraw.addEventListener("click", ()=>{ withdrawModal.classList.remove("hidden"); withdrawMsg.textContent=""; });
}
if(closeWithdraw && withdrawModal){
  closeWithdraw.addEventListener("click", ()=>{ withdrawModal.classList.add("hidden"); });
}
if(withdrawBtn && withdrawModal){
  withdrawBtn.addEventListener("click", ()=>{ withdrawModal.classList.remove("hidden"); withdrawMsg.textContent=""; });
}

if(submitWithdraw){
  submitWithdraw.addEventListener("click", async ()=>{
    const amount = parseFloat(withdrawAmount.value || "0");
    const method = withdrawMethod.value;
    const details = withdrawDetails.value || "";
    if(isNaN(amount) || amount < parseFloat(withdrawAmount.min || "500")){
      withdrawMsg.textContent = `Minimum withdrawal is KES ${withdrawAmount.min}`;
      return;
    }
    try{
      const res = await fetch("/api/withdraw", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({amount, method, details})
      });
      const j = await res.json();
      if(j.error){
        withdrawMsg.textContent = j.error;
      }else{
        withdrawMsg.textContent = j.message || "Withdrawal request submitted.";
        await fetchBalance();
        setTimeout(()=>{ withdrawModal.classList.add("hidden"); }, 1200);
      }
    }catch(e){
      withdrawMsg.textContent = "Request failed";
    }
  });
}

if(modeDemoBtn) modeDemoBtn.addEventListener("click", ()=> setMode("demo"));
if(modeRealBtn) modeRealBtn.addEventListener("click", ()=> setMode("real"));
if(spinBtn) spinBtn.addEventListener("click", spin);

window.addEventListener("load", ()=>{
  populateSymbols();
  fetchSettings();
  fetchBalance();
  setMode("demo");
  if(reelsEls[0]){
    animateReels([
      [SYMBOLS[0],SYMBOLS[1],SYMBOLS[2]],
      [SYMBOLS[3],SYMBOLS[4],SYMBOLS[5]],
      [SYMBOLS[6],SYMBOLS[7],SYMBOLS[8]]
    ]);
  }
});


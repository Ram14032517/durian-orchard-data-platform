const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const {chromium}=require('C:/Users/support/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const pdf=path.join(__dirname,'binary_classification_report_th.pdf');if(fs.existsSync(pdf))throw Error('Refuse overwrite');
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const page=await browser.newPage();await page.route(/^https?:/,r=>r.abort());await page.goto(pathToFileURL(path.join(__dirname,'binary_classification_report_th.html')).href);await page.emulateMedia({media:'print'});await page.evaluate(()=>document.fonts.ready);
 const layout=await page.locator('.page').evaluateAll(ns=>ns.map((n,i)=>({page:i+1,height:n.clientHeight,scrollHeight:n.scrollHeight,width:n.clientWidth,scrollWidth:n.scrollWidth,bottom:Math.max(...Array.from(n.children).filter(c=>c.tagName!=='FOOTER').map(c=>c.getBoundingClientRect().bottom-n.getBoundingClientRect().top)),footer:n.querySelector('footer').getBoundingClientRect().top-n.getBoundingClientRect().top})));
 console.log(JSON.stringify(layout));if(layout.some(n=>n.bottom>n.footer-12||n.scrollHeight>n.height+2||n.scrollWidth>n.width+2))throw Error('Layout overflow; do not generate PDF');
 await page.pdf({path:pdf,format:'A4',printBackground:true,preferCSSPageSize:true});await browser.close();fs.writeFileSync(path.join(__dirname,'pdf_layout_verification.json'),JSON.stringify({layout,network:'blocked',fonts:'Leelawadee UI',vector_charts:true},null,2),{flag:'wx'});
})();

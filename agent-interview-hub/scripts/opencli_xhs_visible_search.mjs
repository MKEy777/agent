// A visible-window OpenCLI workflow for XHS accounts using the AI search layout.
// All browser operations use the installed OpenCLI command surface.
import { execFileSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const [main, query] = process.argv.slice(2);
if (!main || !query?.trim()) {
  console.error('Usage: node opencli_xhs_visible_search.mjs <opencli-main.js> <query>');
  process.exit(2);
}
const packageDir = resolve(dirname(main), '../..');
const session = `interview-collector-${process.pid}`;
const call = (args, timeout = 65000) => {
  let output;
  try {
    output = execFileSync(process.execPath, [main, ...args], {
      encoding: 'utf8', timeout, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch (error) {
    throw new Error((error.stdout?.toString().trim() || error.message).slice(0, 1400));
  }
  const envelope = JSON.parse(output.trim());
  if (!envelope.ok) throw new Error(JSON.stringify(envelope.error));
  return envelope.data;
};
const page = (...args) => call(['browser', '--session', session, ...args]);
let windowId;
let bound = false;
let result;
let failure;
try {
  const adapter = await import(pathToFileURL(resolve(packageDir, 'clis/xiaohongshu/search.js')));
  const created = call(['browser', 'chrome', 'call', 'windows.create', JSON.stringify([{
    url: 'https://www.xiaohongshu.com/explore', focused: true, state: 'normal',
    left: 100, top: 100, width: 1280, height: 900,
  }])]);
  windowId = created.id;
  page('bind');
  bound = true;
  const control = page('eval', `
    (async () => {
      for (let n = 0; n < 100; n++) {
        const text = document.body?.innerText || '';
        if (location.pathname.startsWith('/website-login/captcha') ||
            /请求太频繁|访问频次异常|安全限制|Requests too frequent|Scan with logged-in/i.test(text))
          return {error:'SECURITY_BLOCK'};
        if (document.querySelector('#login-btn') || /登录后查看搜索结果/.test(text))
          return {error:'AUTH_REQUIRED'};
        const inputs = Array.from(document.querySelectorAll('input#search-input,textarea[name="aiSearchTextarea"]'))
          .filter(e => {
            const r = e.getBoundingClientRect();
            if (!r.width || !r.height || e.disabled || e.readOnly ||
                e.closest('[hidden],[inert],[aria-hidden="true"]')) return false;
            for (let p=e; p; p=p.parentElement) {
              const s=getComputedStyle(p);
              if (s.display==='none' || s.visibility==='hidden' || Number(s.opacity)<0.01) return false;
            }
            return true;
          });
        if (inputs.length>1) return {error:'AMBIGUOUS_SEARCH_INPUT'};
        if (inputs.length===1 && document.visibilityState==='visible')
          return {id:inputs[0].id,visibility:document.visibilityState};
        await new Promise(r=>setTimeout(r,100));
      }
      return {error:'SEARCH_INPUT_NOT_AVAILABLE'};
    })()
  `);
  if (control.error) throw new Error(control.error);
  if (control.visibility !== 'visible') throw new Error('Search window must remain visible.');
  page('fill', `#${control.id}`, query);
  page('keys', 'Enter');
  const navigation = page('eval', `
    (async () => {
      const query=${JSON.stringify(query)};
      for(let n=0;n<100;n++) {
        if(location.pathname.startsWith('/website-login/captcha')) return {error:'SECURITY_BLOCK'};
        let keyword=new URLSearchParams(location.search).get('keyword');
        if(keyword!==query && keyword?.includes('%')) {
          try {keyword=decodeURIComponent(keyword);} catch {}
        }
        if(['/search_result','/search_result_ai'].includes(location.pathname) && keyword===query)
          return {path:location.pathname};
        await new Promise(r=>setTimeout(r,100));
      }
      return {error:'SEARCH_NAVIGATION_TIMEOUT'};
    })()
  `);
  if (navigation.error) throw new Error(navigation.error);
  const content = page('eval', adapter.__test__.WAIT_FOR_CONTENT_JS);
  if (content !== 'content') throw new Error(`Search content: ${content}`);
  const harvest = page('eval', adapter.buildScrollHarvestJs('www.xiaohongshu.com', 20, {
    maxRounds: 16, budgetMs: 20000, step: 700,
  }));
  if (harvest.diag.securityBlock) throw new Error('SECURITY_BLOCK');
  if (harvest.diag.cardCount > 1 && harvest.diag.feedClientHeight === 0 &&
      harvest.diag.distinctCardTops === 1) throw new Error('Search result layout is collapsed.');
  const rows = harvest.rows.filter(x => x.title?.trim()).slice(0, 20).map((x,i) => ({
    rank:i+1, title:x.title, author:x.author, likes:x.likes, url:x.url, published_at:null,
  }));
  if (!rows.length) throw new Error('No titled search results.');
  result = {ok:true, data:rows, metadata:{method:'opencli-visible-window',query,layout:navigation.path}};
} catch (error) {
  failure = error;
} finally {
  let released = !bound;
  if (bound) {
    try {page('unbind'); released=true;} catch {}
  }
  // Only close the ordinary window created by this invocation, after unbinding.
  if (released && windowId !== undefined) {
    try {call(['browser','chrome','call','windows.remove',JSON.stringify([windowId])]);} catch {}
  }
}
if (failure) {
  console.error(failure.message);
  process.exitCode=1;
} else {
  console.log(JSON.stringify(result));
}

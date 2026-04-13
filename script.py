# -*- coding: utf-8 -*-
import io

with io.open('d:/Project/Mengko/MengkoAI/flow2api-main/static/manage.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add HTML chunk
h1 = '                            <p class="text-xs text-muted-foreground mt-1">选择验证码获取方式</p>\n                        </div>'
h2 = '''                            <p class="text-xs text-muted-foreground mt-1">选择验证码获取方式</p>
                        </div>
                        
                        <div>
                            <div class="flex items-center justify-between mb-2">
                                <label class="text-sm font-medium">打码重试次数</label>
                                <label class="inline-flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox" id="cfgCaptchaInfiniteRetries" class="h-4 w-4 rounded border-input" onchange="toggleCaptchaInfiniteRetries()">
                                    <span class="text-xs font-medium">直到成功</span>
                                </label>
                            </div>
                            <input id="cfgCaptchaMaxRetries" type="number" min="1" max="100" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" placeholder="3" value="3">
                            <p class="text-xs text-muted-foreground mt-1">全局控制打码失败后的重试策略</p>
                        </div>'''
content = content.replace(h1, h2)

# Insert JS for toggle
content = content.replace('loadPluginConfig=async()=>{', '''toggleCaptchaInfiniteRetries=()=>{const inf=document.getElementById("cfgCaptchaInfiniteRetries").checked;document.getElementById("cfgCaptchaMaxRetries").disabled=inf;},
        loadPluginConfig=async()=>{''')

# Insert JS for loading
l1 = "$('cfgPersonalIdleTTL').value=d.personal_idle_tab_ttl_seconds||600;toggleCaptchaOptions();"
l2 = "$('cfgPersonalIdleTTL').value=d.personal_idle_tab_ttl_seconds||600;const retries=d.captcha_max_retries!==undefined?d.captcha_max_retries:3;if(retries<=0){$('cfgCaptchaInfiniteRetries').checked=true;$('cfgCaptchaMaxRetries').value=3;$('cfgCaptchaMaxRetries').disabled=true;}else{$('cfgCaptchaInfiniteRetries').checked=false;$('cfgCaptchaMaxRetries').value=retries;$('cfgCaptchaMaxRetries').disabled=false;}toggleCaptchaOptions();"
content = content.replace(l1, l2)

# Insert JS for saving
s1 = "personalIdleTTL=parseInt($('cfgPersonalIdleTTL').value)||600;const finalProxyEnabled"
s2 = "personalIdleTTL=parseInt($('cfgPersonalIdleTTL').value)||600;let captchaMaxRetries=$('cfgCaptchaInfiniteRetries').checked?-1:(parseInt($('cfgCaptchaMaxRetries').value)||3);const finalProxyEnabled"
content = content.replace(s1, s2)

s3 = "personal_idle_tab_ttl_seconds:personalIdleTTL})"
s4 = "personal_idle_tab_ttl_seconds:personalIdleTTL,captcha_max_retries:captchaMaxRetries})"
content = content.replace(s3, s4)

with io.open('d:/Project/Mengko/MengkoAI/flow2api-main/static/manage.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("HTML edit done")

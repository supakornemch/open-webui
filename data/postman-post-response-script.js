// ============================================================
// Postman Post-Response Script (ใส่ในแท็บ Tests / Post-response)
// ใช้กับ request KB Retrieve — แปลง JSON raw → ข้อความอ่านง่าย
// ============================================================

const jsonData = pm.response.json();

if (jsonData.error) {
    pm.test(`❌ Error: ${jsonData.error.message}`, () => pm.expect.fail());
    return;
}

let output = '';
let found = false;

// --- Activity Summary ---
for (const a of jsonData.activity || []) {
    if (a.type === 'searchIndex') {
        output += `🔍 ค้นหา: ${a.count} ผลลัพธ์ (${a.elapsedMs}ms)\n`;
        if (a.count > 0) found = true;
    } else if (a.type === 'agenticReasoning') {
        output += `🧠 Reasoning: ${a.reasoningTokens} tokens\n`;
    }
}

// --- Response Content ---
for (const r of jsonData.response || []) {
    for (const c of r.content || []) {
        if (c.type === 'text' && c.text && c.text !== '[]') {
            const results = JSON.parse(c.text);
            output += `\n📄 พบ ${results.length} เอกสาร:\n`;
            results.forEach((doc, i) => {
                const content = doc.content || '(ไม่มีเนื้อหา)';
                const truncated = content.length > 400 ? content.substring(0, 400) + '...' : content;
                output += `\n--- ผลลัพธ์ที่ ${i + 1} ---\n`;
                output += `📌 ${doc.title}\n`;
                output += `📝 ${truncated}\n`;
            });
        } else if (c.text === '[]') {
            output += '\n❌ ไม่พบเอกสารที่เกี่ยวข้อง';
        }
    }
}

// --- แสดงผล ---
if (output) {
    console.log(output);
    pm.visualizer.set(`
        <pre style="
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 13px;
            line-height: 1.6;
            padding: 16px;
            background: #f8f9fa;
            border-radius: 8px;
            white-space: pre-wrap;
            word-wrap: break-word;
        ">${output}</pre>
    `);
    pm.test('✅ Retrieve สำเร็จ', () => pm.response.to.have.status(200));
} else {
    pm.test('⚠️ ไม่มี response content', () => pm.expect.fail());
}

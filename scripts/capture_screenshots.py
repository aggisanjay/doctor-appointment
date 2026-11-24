import asyncio
import os
import sys

from playwright.async_api import async_playwright

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

OUTPUT_DIR = os.path.abspath("screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def capture():
    print(f"Using browser at: {CHROME_PATH}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
        )

        viewports = [
            ("desktop", 1440, 900),
            ("mobile", 390, 844),
        ]

        for vp_name, width, height in viewports:
            print(f"\n--- Capturing {vp_name} ({width}x{height}) ---")
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                permissions=["microphone"],
            )
            page = await context.new_page()

            # 1. Idle dashboard
            await page.goto("http://127.0.0.1:5173", wait_until="networkidle")
            await page.wait_for_timeout(1000)
            idle_path = os.path.join(OUTPUT_DIR, f"{vp_name}_1_idle.png")
            await page.screenshot(path=idle_path, full_page=(vp_name == "mobile"))
            print(f"Saved: {idle_path}")

            # 2. Ringing state (click Try Call)
            try_call_btn = page.locator(".try-call-button")
            await try_call_btn.click()
            await page.wait_for_selector(".phone-chassis")
            await page.wait_for_timeout(800)
            ringing_path = os.path.join(OUTPUT_DIR, f"{vp_name}_2_ringing.png")
            await page.screenshot(path=ringing_path)
            print(f"Saved: {ringing_path}")

            # 3. Connected state (inject mock connected state & transcript via window/eval)
            await page.evaluate("""() => {
              // Simulate connected state with transcript
              const chassis = document.querySelector('.phone-chassis');
              if (chassis) {
                chassis.className = 'phone-chassis connected';
                const statusDiv = document.querySelector('.call-status-indicator');
                if (statusDiv) {
                  statusDiv.innerHTML = '<span class="status-connected-timer mono-time">00:42</span>';
                }
                const screenContent = document.querySelector('.phone-screen-content');
                if (screenContent) {
                  // Add in-phone transcript
                  const viewport = document.createElement('div');
                  viewport.className = 'phone-transcript-viewport';
                  viewport.innerHTML = `
                    <div class="phone-transcript-list">
                      <div class="phone-bubble bot"><span class="phone-bubble-sender">Maya</span><p class="phone-bubble-content">Hello, thank you for calling City Care Clinic. How can I help you today?</p></div>
                      <div class="phone-bubble user"><span class="phone-bubble-sender">You</span><p class="phone-bubble-content">I'd like to book an appointment with Dr. Priya Iyer tomorrow morning.</p></div>
                      <div class="phone-bubble bot"><span class="phone-bubble-sender">Maya</span><p class="phone-bubble-content">Dr. Priya Iyer has slots available at 09:00 AM and 09:30 AM tomorrow. Which time would you prefer?</p></div>
                      <div class="phone-bubble user"><span class="phone-bubble-sender">You</span><p class="phone-bubble-content">09:00 AM works. My name is Rajesh Patel and number is 9876543210.</p></div>
                      <div class="phone-bubble bot"><span class="phone-bubble-sender">Maya</span><p class="phone-bubble-content">I have your number as 9 8 7 6 5, 4 3 2 1 0. Is that correct?</p></div>
                    </div>
                  `;
                  screenContent.appendChild(viewport);
                }
              }
            }""")
            await page.wait_for_timeout(500)
            connected_path = os.path.join(OUTPUT_DIR, f"{vp_name}_3_connected.png")
            await page.screenshot(path=connected_path)
            print(f"Saved: {connected_path}")

            # 4. Confirmation card inside phone
            await page.evaluate("""() => {
              const screenContent = document.querySelector('.phone-screen-content');
              if (screenContent) {
                const confCard = document.createElement('div');
                confCard.className = 'confirmation-card booked';
                confCard.innerHTML = `
                  <div class="card-badge">
                    <span class="card-heading">Booking Confirmed</span>
                  </div>
                  <div class="card-details">
                    <div class="card-doc">Dr. Priya Iyer (Cardiology)</div>
                    <div class="card-datetime mono-time">Tomorrow at 09:00 AM • APT-1001</div>
                  </div>
                `;
                screenContent.insertBefore(confCard, screenContent.firstChild.nextSibling);
              }
              // Also highlight a row in dashboard if visible
              const firstRow = document.querySelector('.table-row');
              if (firstRow) firstRow.className = 'table-row row-highlight';
            }""")
            await page.wait_for_timeout(500)
            conf_path = os.path.join(OUTPUT_DIR, f"{vp_name}_4_confirmation_card.png")
            await page.screenshot(path=conf_path)
            print(f"Saved: {conf_path}")

            # 5. Ended state
            await page.evaluate("""() => {
              const chassis = document.querySelector('.phone-chassis');
              if (chassis) {
                chassis.className = 'phone-chassis ended';
                const statusDiv = document.querySelector('.call-status-indicator');
                if (statusDiv) {
                  statusDiv.innerHTML = '<span class="status-ended-text">Call Ended</span>';
                }
                const screenContent = document.querySelector('.phone-screen-content');
                if (screenContent) {
                  screenContent.innerHTML = `
                    <div class="phone-ended-view">
                      <p class="ended-summary">Call ended after <span class="mono-time">01:15</span></p>
                      <p class="ended-note">Your appointment with Dr. Priya Iyer is confirmed and saved on the dashboard.</p>
                    </div>
                  `;
                }
                const muteBtn = document.querySelector('.mute-button');
                if (muteBtn) muteBtn.remove();
              }
            }""")
            await page.wait_for_timeout(500)
            ended_path = os.path.join(OUTPUT_DIR, f"{vp_name}_5_ended.png")
            await page.screenshot(path=ended_path)
            print(f"Saved: {ended_path}")

            await context.close()

        await browser.close()
        print("\nALL SCREENSHOTS CAPTURED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(capture())

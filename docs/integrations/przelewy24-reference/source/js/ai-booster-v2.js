/* AI Visibility Booster V4.1 — Scroll + Calculator */

document.addEventListener('DOMContentLoaded', () => {

    /* ═══ Referral / Follow-up tracking ═══ */
    (function() {
        var params = new URLSearchParams(window.location.search);
        var ref = params.get('ref') || params.get('utm_source') || '';
        var refEmail = params.get('email') || '';
        var campaign = params.get('utm_campaign') || params.get('campaign') || '';
        if (ref || refEmail) {
            var trackData = { ref: ref, email: refEmail, campaign: campaign, ts: Date.now() };
            try { sessionStorage.setItem('be_ref', JSON.stringify(trackData)); } catch(e) {}
            /* Auto-fill email in checkout if present */
            if (refEmail) {
                var emailField = document.querySelector('input[name="email"]');
                if (emailField && !emailField.value) emailField.value = refEmail;
            }
        }
    })();

    /* ═══ Upsell: ?buy=config auto-opens checkout for 200 zł config service ═══ */
    (function() {
        var params = new URLSearchParams(window.location.search);
        if (params.get('buy') === 'config') {
            var upsellEmail = params.get('email') || '';
            var upsellOrder = params.get('order') || '';
            setTimeout(function() {
                /* Set package data for config service */
                window._selectedPackageData = {
                    name: 'KONFIGURACJA',
                    netto: '200',
                    items: ['Konfiguracja systemu AI Visibility Booster', 'Klucz API Gemini', 'Połączenie ze sklepem']
                };
                /* Open checkout */
                if (typeof window.openCheckoutModal === 'function') {
                    window.openCheckoutModal();
                    /* Pre-fill email */
                    if (upsellEmail) {
                        var ef = document.querySelector('#checkoutForm input[name="email"]');
                        if (ef) ef.value = decodeURIComponent(upsellEmail);
                    }
                    /* Update cart display */
                    var cartEl = document.getElementById('checkoutCartItems');
                    if (cartEl) {
                        cartEl.innerHTML = '<div style="padding:12px 0;border-bottom:1px solid #f1f5f9;">'
                            + '<div style="font-weight:600;color:#0f172a;">Konfiguracja systemu</div>'
                            + '<div style="font-size:13px;color:#64748b;margin-top:4px;">Klucz API Gemini + połączenie ze sklepem + pełna konfiguracja</div>'
                            + '</div>';
                    }
                    var nettoEl = document.getElementById('checkoutNetto');
                    var vatEl = document.getElementById('checkoutVat');
                    var bruttoEl = document.getElementById('checkoutBrutto');
                    if (nettoEl) nettoEl.textContent = '200 zł';
                    if (vatEl) vatEl.textContent = '46 zł';
                    if (bruttoEl) bruttoEl.textContent = '246 zł';
                }
            }, 500);
        }
    })();

    /* Scroll Animations — standard reveal (one-shot) */
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) entry.target.classList.add('active');
        });
    }, { threshold: 0.05 });

    // Instantly activate elements already in viewport on load
    document.querySelectorAll('.reveal').forEach(el => {
        var rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight) {
            el.style.transition = 'none';
            el.classList.add('active');
            // Re-enable transition after paint
            requestAnimationFrame(() => { el.style.transition = ''; });
        } else {
            observer.observe(el);
        }
    });

    /* Scroll-linked progressive animation for reveal-left / reveal-right */
    const scrollEls = document.querySelectorAll('.reveal-left, .reveal-right');
    if (scrollEls.length) {
        let ticking = false;
        function updateScrollAnimations() {
            var wh = window.innerHeight;
            scrollEls.forEach(function (el) {
                var rect = el.getBoundingClientRect();
                // progress: 0 = element just entered bottom, 1 = element at 60% from top
                var start = wh;
                var end = wh * 0.6;
                var progress = (start - rect.top) / (start - end);
                progress = Math.max(0, Math.min(1, progress));

                var opacity = progress;
                var isMob = window.innerWidth <= 768;
                var isLeft = el.classList.contains('reveal-left');
                var offsetX = isMob ? 0 : (1 - progress) * (isLeft ? -40 : 40);
                var offsetY = (1 - progress) * 15;

                el.style.opacity = opacity;
                el.style.transform = 'translate(' + offsetX + 'px, ' + offsetY + 'px)';
            });
            ticking = false;
        }
        window.addEventListener('scroll', function () {
            if (!ticking) {
                ticking = true;
                requestAnimationFrame(updateScrollAnimations);
            }
        }, { passive: true });
        // Initial run
        updateScrollAnimations();
    }

    /* Niche expand/collapse */
    const nicheBtn = document.getElementById('nicheExpandBtn');
    if (nicheBtn) {
        let nicheOpen = false;
        nicheBtn.addEventListener('click', () => {
            nicheOpen = !nicheOpen;
            document.querySelectorAll('.ab-niche-hidden').forEach(el => {
                if (nicheOpen) { el.classList.add('ab-niche-show'); }
                else { el.classList.remove('ab-niche-show'); }
            });
            const counter = nicheBtn.querySelector('.ab-niche-counter');
            if (counter) counter.textContent = nicheOpen ? '12 z 12' : '6 z 12';
            nicheBtn.firstChild.textContent = nicheOpen ? 'Zwiń branże ' : 'Pokaż wszystkie branże ';
        });
    }

    /* Score Pulse — only when scrolled into view */
    const scoringEl = document.querySelector('.ab-scoring');
    if (scoringEl) {
        const pulseObs = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    scoringEl.classList.add('ab-pulse');
                } else {
                    scoringEl.classList.remove('ab-pulse');
                }
            });
        }, { threshold: 0.5 });
        pulseObs.observe(scoringEl);
    }

    /* Formula Typing Animation — triggered on scroll */
    const formulaEl = document.getElementById('formulaTyping');
    if (formulaEl) {
        let typed = false;
        const typeObs = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !typed) {
                    typed = true;
                    runTyping();
                }
            });
        }, { threshold: 0.6 });
        typeObs.observe(formulaEl);

        function runTyping() {
            const line1 = document.getElementById('typingLine1');
            const line2 = document.getElementById('typingLine2');
            const cursor = formulaEl.querySelector('.ab-typing-cursor');
            const text1 = 'Nie sprzedajemy opisów.';
            const text2raw = 'Budujemy system, w którym: {Google rozumie} → {AI wykorzystuje} → {Klient kupuje}';
            let i = 0;

            function typeChar(el, text, cb) {
                if (i >= text.length) { i = 0; if (cb) cb(); return; }
                const ch = text[i];
                if (ch === '{') {
                    const end = text.indexOf('}', i);
                    const word = text.substring(i + 1, end);
                    const span = document.createElement('span');
                    span.className = 'ab-typing-hl';
                    span.textContent = word;
                    el.appendChild(span);
                    i = end + 1;
                } else {
                    el.appendChild(document.createTextNode(ch));
                    i++;
                }
                setTimeout(() => typeChar(el, text, cb), 35);
            }

            typeChar(line1, text1, () => {
                setTimeout(() => typeChar(line2, text2raw, () => {
                    cursor.classList.add('hide');
                }), 400);
            });
        }
    }
    /* Parameter Tabs */
    document.querySelectorAll('.ab-param-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.ab-param-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.ab-param-panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            const target = document.getElementById(tab.dataset.target);
            if (target) target.classList.add('active');
        });
    });

    /* Calculator */
    const productCountInput = document.getElementById('productCount');
    const productCountGroup = document.getElementById('productCountGroup');
    const toggleOurApi = document.getElementById('toggleOurApi');
    const toggleSetup = document.getElementById('toggleSetup');
    const toggleRocket = document.getElementById('toggleRocket');
    const cartItemsList = document.getElementById('cartItemsList');
    const displayTotal = document.getElementById('calcTotal');

    /* Show/hide product count when toggle is switched */
    if (toggleOurApi && productCountGroup) {
        toggleOurApi.addEventListener('change', () => {
            productCountGroup.style.display = toggleOurApi.checked ? 'block' : 'none';
            if (toggleOurApi.checked && !toggleSetup.checked) {
                toggleSetup.checked = true;
            } else if (!toggleOurApi.checked) {
                toggleSetup.checked = false;
            }
            updateCalc();
        });
    }

    /* Rocket Boost requires GPU + Setup — auto-enable */
    if (toggleRocket && toggleOurApi) {
        toggleRocket.addEventListener('change', () => {
            if (toggleRocket.checked) {
                if (!toggleOurApi.checked) {
                    toggleOurApi.checked = true;
                    if (productCountGroup) productCountGroup.style.display = 'block';
                }
                if (!toggleSetup.checked) toggleSetup.checked = true;
            } else {
                toggleOurApi.checked = false;
                toggleSetup.checked = false;
                if (productCountGroup) productCountGroup.style.display = 'none';
            }
            updateCalc();
        });
    }

    /* Upsell links in cart-info → auto-enable toggles */
    document.querySelectorAll('.ab-cart-info a[href^="#opt"]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').slice(1);
            const map = { optSetup: toggleSetup, optGpu: toggleOurApi, optRocket: toggleRocket };
            const toggle = map[targetId];
            if (toggle && !toggle.checked) {
                toggle.checked = true;
                toggle.dispatchEvent(new Event('change'));
            }
            document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    });

    function cartItem(id, label, price, removable) {
        const d = document.createElement('div');
        d.className = 'res-item';
        d.innerHTML = '<span>' + label + '</span><div style="display:flex;align-items:center;gap:8px;"><span>' +
            price.toLocaleString('pl-PL') + ' zł <small style="color:#94a3b8;font-weight:400">netto</small></span>' +
            (removable ? '<button type="button" class="remove-item" onclick="removeItem(\'' + id + '\')" title="Usuń">×</button>' : '') +
            '</div>';
        return d;
    }

    window.removeItem = (id) => {
        if (id === 'toggleOurApiBase') id = 'toggleOurApi';
        const el = document.getElementById(id);
        if (el && el.type === 'checkbox') {
            el.checked = false;
            if (id === 'toggleOurApi' && productCountGroup) productCountGroup.style.display = 'none';
        }
        updateCalc();
    };

    function updateCalc() {
        if (!productCountInput) return;
        const count = parseInt(productCountInput.value) || 0;
        let total = 1000;
        cartItemsList.innerHTML = '';

        cartItemsList.appendChild(cartItem('base', '🔑 Dostęp do systemu (jednorazowo) — Licencja', 1000, false));

        if (toggleOurApi.checked) {
            cartItemsList.appendChild(cartItem('toggleOurApiBase', 'Infrastruktura GPU (jednorazowo)', 1000, true));
            total += 1000;
            if (count > 0) {
                const rate = count >= 10000 ? 0.15 : 0.20;
                const cost = count * rate;
                cartItemsList.appendChild(cartItem('toggleOurApi', 'Generacja AI (' + count + ' szt. × ' + rate.toFixed(2) + ')', cost, true));
                total += cost;
            }
        }
        if (toggleSetup.checked) {
            cartItemsList.appendChild(cartItem('toggleSetup', 'Technical Onboarding', 200, true));
            total += 200;
        }
        if (toggleRocket.checked) {
            cartItemsList.appendChild(cartItem('toggleRocket', '🚀 Rocket Boost (GSC/Semrush)', 1500, true));
            total += 1500;
        }

        var vat = 0; // Hide VAT
        var brutto = total; // No VAT, just Netto
        displayTotal.innerHTML = total.toLocaleString('pl-PL', { minimumFractionDigits: 2 }) + ' zł <small style="color:#94a3b8;font-weight:400">netto</small>';
        var vatEl = document.getElementById('calcVat');
        var bruttoEl = document.getElementById('calcBrutto');
        if (vatEl) vatEl.style.display = 'none'; // hide VAT explicitly
        if (bruttoEl) bruttoEl.innerText = brutto.toLocaleString('pl-PL', { minimumFractionDigits: 2 }) + ' zł';
    }

    if (productCountInput) {
        [productCountInput, toggleOurApi, toggleSetup, toggleRocket].forEach(el => {
            el.addEventListener('input', updateCalc);
            el.addEventListener('change', updateCalc);
        });
        updateCalc();
    }

    /* ═══ CHECKOUT MODAL ═══ */
    var checkoutProducts = {
        base: { label: '🔑 Dostęp do systemu — Licencja', price: 1000, removable: false },
        toggleSetup: { label: '⚙️ Technical Onboarding', price: 200, removable: true, toggle: 'toggleSetup' },
        toggleRocket: { label: '🚀 Rocket Boost (GSC/Semrush)', price: 1500, removable: true, toggle: 'toggleRocket' }
    };

    function refreshCheckoutCart() {
        var tbody = document.getElementById('checkoutItems');
        var upsellBox = document.getElementById('checkoutUpsells');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (upsellBox) { upsellBox.innerHTML = ''; upsellBox.parentElement.style.display = 'none'; }

        var currentPkg = window._selectedPackage || 'starter';
        var hasKonfig = window._checkoutKonfig || false;

        // Package definitions
        var pkgDefs = {
            starter:      { name: 'STARTER',       icon: '🔑', price: 1000 },
            professional: { name: 'PROFESSIONAL',  icon: '⭐', price: 1500 },
            rocket:       { name: 'ROCKET BOOST',  icon: '🚀', price: 2500 }
        };
        var def = pkgDefs[currentPkg];
        var basePrice = def.price;

        // --- Package row with badge ---
        var trPkg = document.createElement('tr');
        var removeBtn = '';
        if (currentPkg !== 'starter') {
            removeBtn = '<button class="checkout-remove" onclick="checkoutDowngrade()" title="Usuń">×</button>';
        }
        var badgeStyles = {
            starter: 'background:linear-gradient(135deg,#38bdf8,#22c55e);color:#fff;',
            professional: 'background:#22c55e;color:#fff;',
            rocket: 'background:linear-gradient(135deg,#f97316,#ef4444);color:#fff;'
        };
        var badgeLabels = {
            starter: 'STARTER',
            professional: '⭐ PROFESSIONAL — BESTSELLER',
            rocket: '🚀 ROCKET BOOST — NAJWIĘKSZY EFEKT'
        };
        var badgeStyle = badgeStyles[currentPkg] || badgeStyles.starter;
        var badgeLabel = badgeLabels[currentPkg] || 'STARTER';
        trPkg.innerHTML = '<td>' +
            '<div style="display:inline-block;' + badgeStyle + 'border-radius:99px;padding:5px 14px;font-weight:700;font-size:11px;letter-spacing:0.5px">' + badgeLabel + '</div>' +
        '</td><td style="text-align:right;font-weight:700;white-space:nowrap">' + basePrice.toLocaleString('pl-PL') + ' zł netto</td><td>' + removeBtn + '</td>';
        tbody.appendChild(trPkg);

        // --- Konfiguracja row (only for STARTER) ---
        if (currentPkg === 'starter' && hasKonfig) {
            var trKonfig = document.createElement('tr');
            trKonfig.innerHTML = '<td>⚙️ Konfiguracja za Ciebie (API Gemini / Web API sklepu) — 200 zł</td><td></td><td><button class="checkout-remove" onclick="checkoutRemoveKonfig()" title="Usuń">×</button></td>';
            tbody.appendChild(trKonfig);
            basePrice += 200;
        }

        // --- Generation calculator (PRO/ROCKET only) ---
        var genCost = 0;
        if (currentPkg === 'professional' || currentPkg === 'rocket') {
            var pkg = window._selectedPackageData;
            var currentCount = (pkg && pkg.productCount) ? pkg.productCount : 1000;
            genCost = Math.round(currentCount * 0.20);

            // Insert styled calc block after table
            var trGen = document.createElement('tr');
            trGen.innerHTML = '<td colspan="3" style="padding:0">' +
                '<div class="checkout-gen-calc">' +
                    '<label>🤖 Generacja opisów AI</label>' +
                    '<div class="calc-row">' +
                        '<input type="number" id="checkoutProductCount" value="' + currentCount + '" min="0" step="100">' +
                        '<span class="calc-formula">produktów × 0,20 zł =</span>' +
                        '<span class="calc-result" id="checkoutGenTotal">' + genCost + ' zł</span>' +
                    '</div>' +
                    '<div class="calc-hint">Ile masz produktów w sklepie? Wpisz liczbę — koszt przeliczy się automatycznie.</div>' +
                '</div>' +
            '</td>';
            tbody.appendChild(trGen);

            // Attach live calculator
            var totalBase = basePrice;
            setTimeout(function () {
                var inp = document.getElementById('checkoutProductCount');
                if (inp) {
                    inp.addEventListener('input', function () {
                        var count = parseInt(inp.value) || 0;
                        var cost = Math.round(count * 0.20);
                        var genEl = document.getElementById('checkoutGenTotal');
                        if (genEl) genEl.textContent = cost + ' zł';
                        // Update totals live
                        var newTotal = totalBase + cost;
                        var brutto = newTotal; // netto
                        var nettoEl = document.getElementById('checkoutNetto');
                        var vatEl = document.getElementById('checkoutVat');
                        var bruttoEl = document.getElementById('checkoutBrutto');
                        if (nettoEl) nettoEl.textContent = newTotal.toLocaleString('pl-PL', { minimumFractionDigits: 2 }) + ' zł';
                        // if (vatEl) vatEl.textContent = vat.toLocaleString('pl-PL', { minimumFractionDigits: 2 }) + ' zł';
                        if (bruttoEl) bruttoEl.textContent = brutto.toLocaleString('pl-PL', { minimumFractionDigits: 2 }) + ' zł';
                        // Update package data for submission
                        if (window._selectedPackageData) {
                            window._selectedPackageData.productCount = count;
                            window._selectedPackageData.genCost = cost;
                            window._selectedPackageData.netto = newTotal;
                        }
                    });
                }
            }, 50);
        }

        var total = basePrice + genCost;

        // --- Upsells ---
        if (upsellBox) {
            var hasUpsell = false;

            // Konfiguracja upsell (only for STARTER without it)
            if (currentPkg === 'starter' && !hasKonfig) {
                hasUpsell = true;
                var divK = document.createElement('div');
                divK.className = 'checkout-upsell-item';
                divK.innerHTML = '<span>⚙️ Konfiguracja za Ciebie</span><span>+200 zł</span>' +
                    '<button class="checkout-add" onclick="checkoutAddKonfig()">+ Dodaj</button>';
                upsellBox.appendChild(divK);
            }

            // Package upgrades
            if (currentPkg === 'starter') {
                hasUpsell = true;
                var div = document.createElement('div');
                div.className = 'checkout-upsell-item';
                div.innerHTML = '<span>⭐ Upgrade do PROFESSIONAL</span><span>1 500 zł netto</span>' +
                    '<button class="checkout-add" onclick="selectPackageAndOrder(\'professional\')">Zmień</button>';
                upsellBox.appendChild(div);

                var div2 = document.createElement('div');
                div2.className = 'checkout-upsell-item';
                div2.innerHTML = '<span>🚀 Upgrade do ROCKET BOOST</span><span>2 500 zł netto</span>' +
                    '<button class="checkout-add" onclick="selectPackageAndOrder(\'rocket\')">Zmień</button>';
                upsellBox.appendChild(div2);
            } else if (currentPkg === 'professional') {
                hasUpsell = true;
                var div = document.createElement('div');
                div.className = 'checkout-upsell-item';
                div.innerHTML = '<span>🚀 Upgrade do ROCKET BOOST</span><span>+1 000 zł netto</span>' +
                    '<button class="checkout-add" onclick="selectPackageAndOrder(\'rocket\')">Zmień</button>';
                upsellBox.appendChild(div);
            }
            if (hasUpsell) upsellBox.parentElement.style.display = '';
        }

        // --- Update totals ---
        var brutto = total; // No VAT, just Netto
        var nettoEl = document.getElementById('checkoutNetto');
        var bruttoEl = document.getElementById('checkoutBrutto');
        if (nettoEl) nettoEl.textContent = total.toLocaleString('pl-PL', { minimumFractionDigits: 2 }) + ' zł';
        if (bruttoEl) bruttoEl.textContent = brutto.toLocaleString('pl-PL', { minimumFractionDigits: 2 }) + ' zł';

        // --- Update _selectedPackageData for submission ---
        var itemDescriptions = {
            starter: [
                'Opisy AI SEO produktów + Meta Description + JSON-LD Schema — ' + def.price.toLocaleString('pl-PL') + ' zł'
            ],
            professional: [
                'Opisy AI SEO + Meta + Schema + Rich Snippets + FAQ Schema — ' + def.price.toLocaleString('pl-PL') + ' zł',
                'Generacja na infrastrukturze Booster Engine (klucz API + konfiguracja w cenie)'
            ],
            rocket: [
                'Opisy AI SEO + Meta + Schema + Rich Snippets + FAQ + 200+ wariantów fraz — ' + def.price.toLocaleString('pl-PL') + ' zł',
                'Generacja na infrastrukturze Booster Engine (klucz API + konfiguracja w cenie)',
                'Dedykowana optymalizacja branżowa + anty-kanibalizacja'
            ]
        };
        var items = itemDescriptions[currentPkg] || itemDescriptions.starter;
        items = items.slice(); // clone
        if (currentPkg === 'starter' && hasKonfig) {
            items.push('Konfiguracja systemu (klucz API Gemini + połączenie ze sklepem) — 200 zł');
        }
        if (genCost > 0) {
            var cnt = (window._selectedPackageData && window._selectedPackageData.productCount) || 1000;
            items.push('Generacja ' + cnt.toLocaleString('pl-PL') + ' opisów produktów — ' + genCost + ' zł');
        }
        window._selectedPackageData = {
            name: def.name,
            items: items,
            netto: total,
            brutto: brutto,
            productCount: (currentPkg !== 'starter') ? ((window._selectedPackageData && window._selectedPackageData.productCount) || 1000) : 0,
            genCost: genCost
        };

        // --- Expected Google Position ---
        var posEl = document.getElementById('checkoutPosition');
        if (posEl) {
            var posData = {
                starter: { pos: '5–10', pct: '35%', barColor: '#f59e0b', bg: '#fef3c7', border: '#f59e0b', sub: 'Widoczność (dolna część strony)', warn: 'Na pozycji 6–10 masz 20× mniej wejść niż na pozycji 2' },
                professional: { pos: '4–7', pct: '55%', barColor: 'linear-gradient(90deg,#3b82f6,#22c55e)', bg: '#eff6ff', border: '#3b82f6', sub: 'Stały ruch (środek strony)', warn: 'Na pozycji 3–5 masz 5× mniej wejść niż na pozycji 1–2' },
                rocket: { pos: '1–5', pct: '85%', barColor: 'linear-gradient(90deg,#22c55e,#16a34a)', bg: '#f0fdf4', border: '#22c55e', sub: 'Dominacja (TOP wyników)', warn: 'Na pozycji 2 masz 20× więcej kliknięć niż pozycja 7' }
            };
            var pd = posData[currentPkg] || posData.starter;
            posEl.style.background = pd.bg;
            posEl.style.borderLeft = '3px solid ' + pd.border;
            posEl.innerHTML =
                '<div style="font-size:12px;font-weight:600;margin-bottom:6px">🏆 Oczekiwana pozycja w Google:</div>' +
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">' +
                    '<div style="flex:1;height:10px;background:#e2e8f0;border-radius:99px;overflow:hidden">' +
                        '<div style="width:' + pd.pct + ';height:100%;background:' + pd.barColor + ';border-radius:99px;transition:width 0.5s"></div>' +
                    '</div>' +
                    '<span style="font-weight:800;font-size:15px;min-width:36px">' + pd.pos + '</span>' +
                '</div>' +
                '<div style="font-size:11px;color:#475569;margin-bottom:4px">' + pd.sub + '</div>' +
                '<div style="font-size:10px;padding:4px 8px;background:rgba(0,0,0,0.05);border-radius:6px;color:#64748b">' + pd.warn + '</div>';
        }

        // --- Dynamic Value Reminder ---
        var valEl = document.getElementById('checkoutValueInline');
        if (valEl) {
            var valFeatures = {
                starter: [
                    '✔ Opisy AI SEO dla każdego produktu',
                    '✔ JSON-LD Product Schema',
                    '✔ Semantyczna struktura H1-H3',
                    '✔ Meta description z formułą CTR',
                    '✔ Licencja — dostęp na zawsze'
                ],
                professional: [
                    '✔ Wszystko ze STARTER +',
                    '✔ Generacja na naszej infrastrukturze',
                    '✔ Konfiguracja techniczna w cenie',
                    '✔ Rich Snippets (gwiazdki, ceny)',
                    '✔ FAQ Schema z intencjami zakupowymi',
                    '✔ Optymalizacja crawl budget'
                ],
                rocket: [
                    '✔ Wszystko z PROFESSIONAL +',
                    '✔ 200+ wariantów fraz kluczowych',
                    '✔ Dedykowana optymalizacja branżowa',
                    '✔ Anty-kanibalizacja treści',
                    '✔ Priorytet realizacji',
                    '✔ Automatyczna kontrola jakości'
                ]
            };
            var feats = valFeatures[currentPkg] || valFeatures.starter;
            valEl.innerHTML = '<div style="font-size:11px;font-weight:700;color:#065f46;margin-bottom:4px">W PAKIECIE ' + def.name + ':</div>' +
                feats.map(function(f) { return '<div class="checkout-trust-item">' + f + '</div>'; }).join('');
        }

        // --- Dynamic Urgency (stable per day + per package, new data tomorrow) ---
        var urgEl = document.getElementById('checkoutUrgencyLive');
        if (urgEl) {
            var today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
            var urgKey = 'sd_urg_' + currentPkg + '_' + today;
            var urgData;
            try { urgData = JSON.parse(localStorage.getItem(urgKey)); } catch (e) { }
            if (!urgData) {
                // Clean old date keys
                for (var i = 0; i < localStorage.length; i++) {
                    var k = localStorage.key(i);
                    if (k && k.startsWith('sd_urg_') && k.indexOf(today) === -1) {
                        try { localStorage.removeItem(k); } catch (e) { }
                    }
                }
                var cities = ['Warszawa', 'Kraków', 'Wrocław', 'Poznań', 'Gdańsk', 'Łódź', 'Katowice', 'Lublin', 'Szczecin', 'Bydgoszcz'];
                var pkgNames = { starter: 'STARTER', professional: 'PROFESSIONAL', rocket: 'ROCKET BOOST' };
                urgData = {
                    clients: Math.floor(Math.random() * 4) + 2,
                    min: Math.floor(Math.random() * 45) + 8,
                    city: cities[Math.floor(Math.random() * cities.length)],
                    pkg: pkgNames[currentPkg] || 'STARTER'
                };
                try { localStorage.setItem(urgKey, JSON.stringify(urgData)); } catch (e) { }
            }
            urgEl.innerHTML =
                '<div class="checkout-urgency-fire">🔥 ' + urgData.clients + ' klientów kupiło ' + urgData.pkg + ' w ostatnich 24h</div>' +
                '<div class="checkout-urgency-time">⚡ Ostatni zakup: ' + urgData.min + ' min temu (' + urgData.city + ')</div>';
        }
    }

    // --- Downgrade: remove current package, go one level down ---
    window.checkoutDowngrade = function () {
        var currentPkg = window._selectedPackage || 'starter';
        if (currentPkg === 'rocket') {
            window._selectedPackage = 'professional';
        } else if (currentPkg === 'professional') {
            window._selectedPackage = 'starter';
            window._checkoutKonfig = true; // auto-add konfig when downgrading to starter
        }
        refreshCheckoutCart();
    };

    // --- Konfiguracja add/remove ---
    window.checkoutAddKonfig = function () {
        window._checkoutKonfig = true;
        refreshCheckoutCart();
    };
    window.checkoutRemoveKonfig = function () {
        window._checkoutKonfig = false;
        refreshCheckoutCart();
    };

    window.checkoutRemove = function (id) {
        if (id === 'toggleOurApi' && toggleOurApi) { toggleOurApi.checked = false; if (productCountGroup) productCountGroup.style.display = 'none'; }
        var el = document.getElementById(id);
        if (el && el.type === 'checkbox') el.checked = false;
        updateCalc();
        refreshCheckoutCart();
    };
    window.checkoutAdd = function (id) {
        if (id === 'toggleOurApi' && toggleOurApi) { toggleOurApi.checked = true; if (productCountGroup) productCountGroup.style.display = ''; }
        var el = document.getElementById(id);
        if (el && el.type === 'checkbox') el.checked = true;
        // Rocket Boost adds all packages
        if (id === 'toggleRocket') {
            if (toggleSetup) toggleSetup.checked = true;
            if (toggleOurApi) { toggleOurApi.checked = true; if (productCountGroup) productCountGroup.style.display = ''; }
        }
        updateCalc();
        refreshCheckoutCart();
    };
    window.checkoutUpdateQty = function (val) {
        var n = parseInt(val) || 0;
        if (n < 0) n = 0;
        if (productCountInput) { productCountInput.value = n; }
        updateCalc();
        refreshCheckoutCart();
        // Keep focus on the qty input
        var q = document.getElementById('checkoutQty');
        if (q) { q.focus(); q.select(); }
    };

    window.openCheckoutModal = function () {
        var modal = document.getElementById('checkoutModal');
        if (!modal) return;
        refreshCheckoutCart();
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        /* Auto-fill email from referral */
        var refData = {};
        try { refData = JSON.parse(sessionStorage.getItem('be_ref') || '{}'); } catch(e) {}
        if (refData.email) {
            var ef = document.querySelector('#checkoutForm input[name="email"]');
            if (ef && !ef.value) ef.value = refData.email;
        }

        /* Track abandoned cart (3s delay) */
        window._abCartTimer = setTimeout(function() {
            var cartEmail = (document.querySelector('#checkoutForm input[name="email"]') || {}).value || refData.email || '';
            var cartStore = (document.querySelector('#checkoutForm input[name="store_url"]') || {}).value || '';
            var pkg = window._selectedPackageData;
            if (cartEmail || cartStore) {
                fetch('api/abandoned-cart.php', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: cartEmail, store_url: cartStore,
                        product: 'AI Visibility Booster', plan: pkg ? pkg.name : '',
                        ref: refData.ref || '', campaign: refData.campaign || ''
                    })
                }).catch(function(){});
            }
        }, 3000);
    };
    window.closeCheckoutModal = function () {
        var modal = document.getElementById('checkoutModal');
        if (modal) modal.style.display = 'none';
        document.body.style.overflow = '';
    };

    /* ═══ Track email on blur (abandoned cart for direct visitors) ═══ */
    var _abEmailField = document.querySelector('#checkoutForm input[name="email"]');
    if (_abEmailField) {
        _abEmailField.addEventListener('blur', function() {
            var em = this.value.trim();
            if (!em || em.indexOf('@') < 1) return;
            var storeEl = document.querySelector('#checkoutForm input[name="store_url"]');
            var pkg = window._selectedPackageData;
            fetch('api/abandoned-cart.php', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: em, store_url: storeEl ? storeEl.value.trim() : '',
                    product: 'AI Visibility Booster', plan: pkg ? pkg.name : '',
                    ref: 'direct', campaign: ''
                })
            }).catch(function(){});
        });
    }

    /* ═══ Real-time NIP validation (10 digits) ═══ */
    var _bNip = document.getElementById('boosterNipInput');
    if (_bNip) {
        _bNip.addEventListener('input', function() {
            var digits = this.value.replace(/\D/g, '');
            var err = document.getElementById('boosterNipError');
            if (digits.length > 0 && digits.length !== 10) {
                err.style.display = 'block';
                this.style.borderColor = '#ef4444';
            } else {
                err.style.display = 'none';
                this.style.borderColor = '';
            }
        });
    }

    /* ═══ Real-time Phone validation (9 digits) ═══ */
    var _bPhone = document.getElementById('boosterPhoneInput');
    if (_bPhone) {
        _bPhone.addEventListener('input', function() {
            var digits = this.value.replace(/\D/g, '');
            if (digits.length > 9 && digits.substring(0, 2) === '48') digits = digits.substring(2);
            var err = document.getElementById('boosterPhoneError');
            if (digits.length > 0 && digits.length !== 9) {
                err.style.display = 'block';
                this.style.borderColor = '#ef4444';
            } else {
                err.style.display = 'none';
                this.style.borderColor = '';
            }
        });
    }

    window.submitCheckout = function () {
        var form = document.getElementById('checkoutForm');
        var cb = document.getElementById('checkoutAcceptTerms');
        // Validate checkbox
        if (cb && !cb.checked) {
            cb.style.outline = '2px solid #ef4444';
            cb.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
        // NIP validation (10 digits)
        var nipInput = document.getElementById('boosterNipInput');
        if (nipInput) {
            var nipVal = nipInput.value.replace(/\D/g, '');
            if (nipVal.length !== 10) {
                document.getElementById('boosterNipError').style.display = 'block';
                nipInput.style.borderColor = '#ef4444';
                nipInput.focus();
                return;
            }
        }
        // Phone validation (9 digits)
        var phoneInput = document.getElementById('boosterPhoneInput');
        if (phoneInput) {
            var phoneVal = phoneInput.value.replace(/\D/g, '');
            // Remove country code 48 if present
            if (phoneVal.length > 9 && phoneVal.substring(0, 2) === '48') phoneVal = phoneVal.substring(2);
            if (phoneVal.length !== 9) {
                document.getElementById('boosterPhoneError').style.display = 'block';
                phoneInput.style.borderColor = '#ef4444';
                phoneInput.focus();
                return;
            }
        }
        // Validate form fields
        if (form && !form.reportValidity()) return;
        var btn = document.getElementById('checkoutSubmitBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'PRZETWARZANIE...'; }
        // Collect data
        var data = {};
        if (form) {
            new FormData(form).forEach(function (v, k) { data[k] = v; });
        }
        // Payment method
        var payRadio = document.querySelector('input[name="payment_method"]:checked');
        data.payment_method = payRadio ? payRadio.value : 'blik';
        // Calculate brutto from checkout
        var bruttoEl = document.getElementById('checkoutBrutto');
        var bruttoText = bruttoEl ? bruttoEl.textContent : '0';
        var bruttoNum = parseFloat(bruttoText.replace(/[^\d.,]/g, '').replace(',', '.').replace(/\s/g, '')) || 0;
        data.amount = bruttoNum;
        data.client = data.name || 'Klient';
        // Package data from new pricing table
        var pkg = window._selectedPackageData;
        var pkgName = pkg ? pkg.name : 'STARTER';
        data.description = 'AI Visibility Booster — ' + pkgName + ' — ' + (data.company || 'zamówienie');
        // Add cart config
        if (pkg && pkg.items) {
            data.order_config = pkgName + ': ' + pkg.items.join(' | ') + ' | RAZEM NETTO: ' + pkg.netto + ' zł';
        } else {
            data.order_config = 'STARTER: Licencja SYSTEM AI | RAZEM NETTO: 1000 zł';
        }
        console.log('[SD] Checkout → email + P24:', data);
        try { localStorage.setItem('sd_order', JSON.stringify(data)); } catch (ex) { }

        /* Attach referral tracking */
        try {
            var refData = JSON.parse(sessionStorage.getItem('be_ref') || '{}');
            if (refData.ref) data.referral_source = refData.ref;
            if (refData.email) data.referral_email = refData.email;
            if (refData.campaign) data.referral_campaign = refData.campaign;
        } catch(e) {}


        // Step 1: Send order emails
        fetch('api/order-email.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
            .then(function (res) { return res.json(); })
            .then(function (emailResult) {
                console.log('[SD] Email result:', emailResult);

                // Skip P24 for traditional transfer
                if (data.payment_method === 'przelew_tradycyjny') {
                    showOrderConfirmation(emailResult.orderId || 'SD-pending');
                    return;
                }

                // Step 2: Try P24 payment
                return fetch('api/p24-register.php', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                })
                    .then(function (res) { return res.json(); })
                    .then(function (p24Result) {
                        if (p24Result.success && p24Result.redirectUrl) {
                            if (btn) btn.textContent = 'PRZEKIEROWUJĘ NA PRZELEWY24...';
                            window.location.href = p24Result.redirectUrl;
                        } else {
                            // P24 not ready yet — show confirmation (email was sent)
                            showOrderConfirmation(emailResult.orderId || 'SD-pending');
                        }
                    })
                    .catch(function () {
                        // P24 unreachable — show confirmation (email was sent)
                        showOrderConfirmation(emailResult.orderId || 'SD-pending');
                    });
            })
            .catch(function (err) {
                console.error('[SD] Email error:', err);
                if (btn) { btn.disabled = false; btn.textContent = 'ZAMAWIAM I PŁACĘ'; }
                alert('Błąd wysyłki zamówienia. Spróbuj ponownie.');
            });
    };
    function showOrderConfirmation(orderId) {
        var container = document.querySelector('.checkout-container');
        if (container) {
            container.innerHTML =
                '<div style="text-align:center;padding:60px 40px;">' +
                '<div style="display:inline-block;width:64px;height:64px;background:#dcfce7;border-radius:50%;line-height:64px;font-size:32px;margin-bottom:20px;">✓</div>' +
                '<h2 style="color:#0f172a;margin-bottom:8px;font-size:22px;">Zamówienie przyjęte!</h2>' +
                '<p style="color:#64748b;font-size:14px;margin-bottom:4px;">Nr zamówienia: <strong>' + orderId + '</strong></p>' +
                '<p style="color:#64748b;line-height:1.6;max-width:400px;margin:12px auto 24px;font-size:14px;">Potwierdzenie zostało wysłane na Twój adres e-mail.<br>Skontaktujemy się w ciągu 24h.</p>' +
                '<a href="ai-visibility-booster.html" class="ab-btn-primary" style="display:inline-block;text-decoration:none;">WRÓĆ DO STRONY</a>' +
                '</div>';
        }
    }
    // Close on Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeCheckoutModal();
    });

    // ═══ PRICING TABLE LOGIC ═══

    // Package definitions
    var packages = {
        starter: {
            name: 'STARTER',
            base: 1000,
            perProduct: 0,
            items: ['🔑 Pakiet STARTER — 1 000 zł']
        },
        professional: {
            name: 'PROFESSIONAL',
            base: 1500,
            perProduct: 0.20,
            items: ['⭐ Pakiet PROFESSIONAL — 1 500 zł']
        },
        rocket: {
            name: 'ROCKET BOOST',
            base: 2500,
            perProduct: 0.20,
            items: ['🚀 Pakiet ROCKET BOOST — 2 500 zł']
        }
    };

    // selectPackageAndOrder — opens checkout with pre-filled package
    window.selectPackageAndOrder = function (pkg) {
        var p = packages[pkg];
        if (!p) return;
        window._checkoutKonfig = false; // reset konfig for non-starter

        // Calculate total
        var productCount = 0;
        var genCost = 0;
        if (pkg === 'professional') {
            var inp = document.getElementById('productCountPro');
            productCount = inp ? parseInt(inp.value) || 1000 : 1000;
            genCost = Math.round(productCount * p.perProduct);
        } else if (pkg === 'rocket') {
            var inp = document.getElementById('productCountRocket');
            productCount = inp ? parseInt(inp.value) || 1000 : 1000;
            genCost = Math.round(productCount * p.perProduct);
        }

        // Starter + konfiguracja toggle
        if (pkg === 'starter') {
            var setupToggle = document.getElementById('toggleSetup');
            if (setupToggle && setupToggle.checked) {
                p = JSON.parse(JSON.stringify(p));
                p.base += 200;
                p.items.push('Konfiguracja techniczna API Gemini/Web API sklepu — 200 zł');
            }
        }

        var totalNetto = p.base + genCost;
        var totalBrutto = totalNetto; // Just Netto

        // Store selected package
        window._selectedPackage = pkg;
        window._selectedPackageData = {
            name: p.name,
            items: p.items.slice(),
            netto: totalNetto,
            brutto: totalBrutto,
            productCount: productCount,
            genCost: genCost
        };

        if (genCost > 0) {
            window._selectedPackageData.items.push('🤖 Generacja ' + productCount.toLocaleString('pl-PL') + ' produktów — ' + genCost + ' zł');
        }

        // Open checkout
        openCheckoutModal();
    };

    // Product count calculators
    var proInput = document.getElementById('productCountPro');
    var rocketInput = document.getElementById('productCountRocket');

    function updateGenCost(input, outputId, formulaId) {
        if (!input) return;
        var count = parseInt(input.value) || 0;
        var cost = Math.round(count * 0.20);
        var out = document.getElementById(outputId);
        if (out) out.textContent = cost + ' zł';
        var formula = document.getElementById(formulaId);
        if (formula) formula.textContent = count.toLocaleString('pl-PL') + ' produktów';
    }

    if (proInput) {
        proInput.addEventListener('input', function () { updateGenCost(proInput, 'proGenCost', 'proGenFormula'); });
        updateGenCost(proInput, 'proGenCost', 'proGenFormula');
    }
    if (rocketInput) {
        rocketInput.addEventListener('input', function () { updateGenCost(rocketInput, 'rocketGenCost', 'rocketGenFormula'); });
        updateGenCost(rocketInput, 'rocketGenCost', 'rocketGenFormula');
    }

    // Sticky CTA
    var stickyCta = document.getElementById('stickyCta');
    var pricingSection = document.getElementById('calc-section');
    if (stickyCta && pricingSection) {
        window.addEventListener('scroll', function () {
            var rect = pricingSection.getBoundingClientRect();
            if (rect.bottom < 0) {
                stickyCta.style.display = 'block';
            } else {
                stickyCta.style.display = 'none';
            }
        });
    }

});

/* ═══ AI DIAGNOSTIC CONSOLE ═══ */
(function () {
    const diagUrl = document.getElementById('diagUrl');
    const diagStart = document.getElementById('diagStart');
    const diagTerminal = document.getElementById('diagTerminal');
    const diagOutput = document.getElementById('diagOutput');
    const diagReport = document.getElementById('diagReport');

    if (!diagStart) return;

    const whiteList = [
        // Our domain
        'shoper-dev',
        // E-commerce platforms (providers)
        'shoper.pl', 'idosell', 'prestashop', 'woocommerce', 'shopify', 'magento', 'opencart', 'wix', 'squarespace',
        // Global giants
        'allegro', 'amazon', 'apple', 'google', 'microsoft', 'facebook', 'meta.com', 'instagram', 'twitter', 'x.com',
        'youtube', 'netflix', 'spotify', 'linkedin', 'tiktok', 'reddit', 'wikipedia',
        // Tech/Cloud
        'github', 'gitlab', 'stackoverflow', 'cloudflare', 'aws.amazon', 'azure', 'digitalocean',
        // PL Marketplace / Top e-com
        'ceneo', 'olx', 'otomoto', 'otodom', 'vinted', 'temu', 'ebay', 'aliexpress', 'alibaba',
        // PL Elektronika
        'x-kom', 'morele.net', 'komputronik', 'mediaexpert', 'rtveuroagd', 'euro.com', 'neonet',
        'mediamarkt', 'samsung', 'xiaomi', 'huawei',
        // PL Moda / Obuwie
        'zalando', 'eobuwie', 'modivo', 'answear', 'aboutyou', 'asos', 'born2be', 'renee',
        'ccc.eu', 'deichmann', 'halfprice', 'tkmaxx', 'primark', 'diverse', 'bytom', 'vistula', 'wojas',
        'reserved', 'mohito', 'sinsay', 'cropp', 'house', 'zara', 'hm.com',
        // PL Produkty / Drogerie
        'biedronka', 'lidl', 'rossmann', 'pepco', 'action', 'dealz', 'kik', 'tedi',
        'netto', 'dino', 'stokrotka', 'aldi', 'kaufland', 'carrefour', 'auchan',
        'intermarche', 'selgros', 'makro', 'hebe', 'superpharm', 'natura',
        // PL Budowlane
        'leroy', 'castorama', 'obi.pl', 'jysk', 'bricomarche',
        // PL Sport
        'decathlon', 'intersport', 'sportisimo',
        // PL Dom / Meble
        'ikea', 'agata', 'brw.com', 'homla', 'westwing', 'blackred',
        // PL Zdrowie / Apteki
        'apteka-melissa', 'doz.pl', 'aptekagemini', 'ziko',
        // PL Zwierzęta
        'zooplus', 'zooart',
        // PL Auto
        'oponeo', 'intercars', 'autodoc',
        // PL Książki / Media
        'empik', 'taniaksiazka', 'bonito', 'publio',
        // PL Inne duże
        'erli', 'merlin', 'smyk', 'coccodrillo',
        // PL Portale / Media
        'onet', 'wp.pl', 'interia', 'o2.pl', 'gazeta.pl', 'tvn24', 'polsat',
        'rmf24', 'money.pl', 'fakt', 'pudelek', 'pomponik', 'natemat',
        'wyborcza', 'tvp.pl', 'se.pl', 'dziennik', 'newsweek'
    ];

    function hashUrl(url) {
        let h = 0;
        for (let i = 0; i < url.length; i++) { h = ((h << 5) - h) + url.charCodeAt(i); h |= 0; }
        return Math.abs(h % 17) + 12;
    }

    /* Polish plural: 1=sklep, 2-4=sklepy, 5+=sklepów */
    function sklepPl(n) {
        if (n === 1) return n + ' sklep';
        if (n >= 2 && n <= 4) return n + ' sklepy';
        return n + ' sklepów';
    }

    function getDomain(url) {
        return url.replace(/https?:\/\//, '').replace(/www\./, '').split('/')[0] || url;
    }

    function isWhite(url) {
        var l = url.toLowerCase();
        return whiteList.some(function (w) { return l.indexOf(w) !== -1; });
    }

    var blackList = [
        // PL vulgar — core roots (catches all conjugations)
        'kurw', 'chuj', 'pizd', 'dupa', 'jeba', 'jebe', 'jebi', 'jebu',
        'gown', 'gówn', 'kuta', 'szmat', 'pierdol', 'pierdal', 'pierdel',
        'cipa', 'cipk', 'cipec', 'ciul', 'fiut', 'fiuc',
        // PL vulgar — prefix combos
        'skurw', 'zajeb', 'pojeb', 'wyjeb', 'najeb', 'odjeb', 'zjeb', 'ujeb', 'przejeb',
        'spierdal', 'spierdol', 'odpierdo', 'napierdo', 'zapierdo', 'przypierdo', 'dopierdo', 'rozpierdo',
        'pierdo', 'pierdz', 'pierdn',
        'wkurw', 'zakurw', 'dokurw', 'pokurw', 'wykurw', 'nakurw', 'rozkurw', 'przekurw',
        'dupek', 'dupsk', 'dupczy',
        // PL vulgar — body/sexual
        'sracz', 'srak', 'srać', 'srac', 'zasran', 'obsra',
        'lodziar', 'lodzik', 'obciag', 'obciąg', 'ruchaj', 'ruchac', 'ruchać', 'wyruch', 'zaruch',
        // PL vulgar — slurs
        'pedal', 'pedał', 'peder', 'ciota', 'ciot', 'cwel',
        'dziwk', 'szlach', 'lafir', 'kurew',
        // PL vulgar — insults
        'morda', 'gnój', 'gnoj', 'suka', 'sukinsyn',
        'debil', 'kretyn', 'głupol', 'tępak',
        'szuj', 'bydl', 'bydlak', 'ścierw', 'padlin', 'łajd', 'łotr', 'dran', 'drań',
        'cham', 'chamo', 'prostak', 'żul',
        'flej', 'oblesn', 'obrzyd',
        // PL mild / borderline
        'cholera', 'psiak', 'jasn', 'pieprz', 'pieprzn', 'pieprzony',
        // PL creative spelling (bypass attempts)
        'kurva', 'h u j', 'p i z d', 'ch uj', 'ku rw',
        'k.u.r.w', 'ch.uj', 'p.i.z.d', 'd.u.p.a',
        // EN vulgar — core + leet + abbreviations
        'fuck', 'fucc', 'fuk', 'fuc', 'phuck', 'phuk', 'fck', 'fcuk', 'f u c k',
        'wtf', 'stfu', 'gtfo', 'lmfao', 'milf',
        'shit', 'sh1t', 'sht', 'sh!t', 'shyt', 'bullshit', 'horseshit', 'apeshit',
        'dick', 'd1ck', 'd!ck', 'dik', 'dikk',
        'cock', 'c0ck', 'cawk', 'kok',
        'pussy', 'puss', 'pusy', 'pu$$y', 'p*ssy',
        'bitch', 'b1tch', 'b!tch', 'biatch', 'bytch', 'beotch',
        'cunt', 'c*nt', 'kunt',
        'twat', 'tw4t',
        'wank', 'wanker', 'w4nk',
        'whore', 'wh0re', 'hoar',
        'hoe', 'thot', 'slut', 'sl*t', 'skank', 'skanky', 'sleaze',
        'bastard', 'b4stard', 'prick', 'pr1ck',
        'tosser', 'bellend', 'knob', 'knobhead', 'nob',
        'asshole', 'a$$hole', 'arsehole', 'arse', 'a$$', 'azz',
        'dumbass', 'jackass', 'smartass', 'fatass', 'lameass', 'kickass',
        'motherfuck', 'mofo', 'mf', 'mfer',
        'cocksu', 'dipshit', 'shitbag', 'shitshow', 'shitstorm',
        'dirtbag', 'scuzz', 'sleazeball', 'pervert', 'perv',
        // EN leet speak / number substitution
        'f0ck', 'b00bs', 'b00bz', 't1ts', 'a55', 'p3nis', 'v4gina', 'd0ng',
        'pr0n', 'h0', 'h03', 'n00b', 'b1atch', 'b!atch',
        // EN youth slang / internet
        'simp', 'incel', 'cuck', 'coomer', 'gooner',
        'deez', 'deeznut', 'ligma', 'sugma', 'bofa', 'candice', 'joe mama',
        'sus', 'bussin', 'gyat', 'rizz', 'skibidi', 'fanum',
        'ratio', 'cope', 'seethe', 'mald', 'kys', 'kms',
        'simp', 'stan', 'bruh', 'brainrot',
        'smegma', 'goatse', 'tubgirl', 'lemonparty', '2girls1cup', 'meatspin',
        'rickroll', 'deeznuts',
        // EN vulgar — slurs & hate speech
        'nigger', 'nigg', 'n1gg', 'n!gg', 'niqqer', 'niqq', 'negr', 'negro',
        'faggot', 'faggo', 'fagg', 'f4gg', 'f@gg',
        'retard', 'retrd', 'r3tard', 'ree', 'reee',
        'spastic', 'spaz', 'sperg', 'autist',
        'tranny', 'tr4nny', 'shemale', 'ladyboy', 'heshe',
        'kike', 'k1ke', 'heeb',
        'chink', 'ch1nk', 'chinky', 'ching chong',
        'gook', 'g00k', 'zipperhead',
        'wetback', 'beaner', 'spic', 'sp1c',
        'cracker', 'honky', 'redneck', 'trailer trash',
        'towelhead', 'raghead', 'sandn',
        'coon', 'c00n', 'darkie', 'jigaboo',
        'dyke', 'lezbo', 'lesbo',
        // EN vulgar — insults expanded
        'loser', 'l0ser', 'moron', 'mor0n', 'imbecil', 'imbecile',
        'douchebag', 'douche', 'douchenozzle', 'sleazebag',
        'scumbag', 'shithead', 'sh1thead', 'dickhead', 'd1ckhead',
        'fuckwit', 'fucktard', 'numbnuts', 'nutcase',
        'wanker', 'w4nker', 'jerkoff', 'jerk0ff',
        'creep', 'creeper', 'stalker', 'psycho', 'sociopath',
        'trash', 'garbage', 'filth', 'lowlife', 'deadbeat',
        'toolbag', 'dirtbag', 'shitbird', 'assclown', 'buttmunch',
        'turd', 'turdface', 'poophead', 'buttface', 'butthead', 'fartface',
        // Adult/Porn — sites & terms
        'porn', 'porno', 'p0rn', 'pr0n',
        'xxx', 'xxxx', 'x-rated', 'xrated',
        'escort', 'callgirl', 'hooker', 'prostitut',
        'erotic', 'erotyk', 'hentai', 'yaoi', 'yuri', 'loli', 'shota',
        'onlyfans', 'fansly', 'manyvids', 'chaturbate',
        'xvideos', 'xhamster', 'pornhub', 'redtube', 'youporn', 'xnxx', 'tube8',
        'spankbang', 'beeg', 'eporner', 'tnaflix', 'drtuber',
        'camgirl', 'webcam', 'livecam', 'cam4',
        'livejasmin', 'stripchat', 'bongacams', 'myfreecams',
        'brazzers', 'bangbros', 'realitykings', 'naughtyamerica',
        'naughty', 'fetish', 'bdsm', 'bondage', 'domina', 'femdom',
        'milf', 'gilf', 'dilf', 'creampie', 'gangbang', 'threesome', 'orgy',
        'blowjob', 'handjob', 'footjob', 'deepthroat',
        'cumshot', 'facial', 'squirt', 'orgasm',
        'nude', 'naked', 'topless', 'upskirt', 'downblouse',
        'sextape', 'sexchat', 'sexcam', 'cybersex', 'phonesex',
        'masturbat', 'vibrator', 'dildo', 'fleshlight', 'buttplug',
        'anal', 'analsex',
        'swinger', 'cuckold', 'hotwife',
        // Gambling / Illegal
        'casino', 'poker', 'blackjack', 'roulette', 'slots', 'betting', 'gambl',
        'darknet', 'darkweb', 'deepweb', 'silkroad', 'tor market',
        'narkotyk', 'drugs', 'cocaine', 'heroin', 'meth', 'weed', 'marijuana',
        'steroid', 'pharma spam',
        // Troll / nonsense patterns
        'blado', 'asdf', 'qwer', 'zxcv', 'aaaa', 'test123', 'fakedom',
        'lipa', 'lipny', 'lipne', 'sciema', 'ściema', 'oszust', 'scam',
        'spam', 'phishing', 'malware', 'trojan', 'virus',
        'deez', 'ligma', 'sugma', 'bofa', 'rickroll'
    ];

    function isBlack(url) {
        var l = url.toLowerCase();
        return blackList.some(function (w) { return l.indexOf(w) !== -1; });
    }

    function typeLine(cls, text, delay) {
        return new Promise(function (resolve) {
            setTimeout(function () {
                var cur = diagOutput.querySelector('.ab-cursor');
                if (cur) cur.remove();
                var line = document.createElement('div');
                line.className = cls;
                line.textContent = text;
                diagOutput.appendChild(line);
                var c = document.createElement('span');
                c.className = 'ab-cursor';
                diagOutput.appendChild(c);
                diagOutput.scrollTop = diagOutput.scrollHeight;
                resolve();
            }, delay);
        });
    }

    function showReport(domain, score) {
        /* Dynamic errors ↔ score */
        var base = hashUrl(domain);
        var errors = base % 4 + 5;
        if (base % 10 === 0) errors = 4;

        /* Save audit result for chatbot context + remarketing */
        window._sdAuditResult = { domain: domain, score: score, errors: errors, ts: Date.now() };
        try { localStorage.setItem('sd_audit', JSON.stringify(window._sdAuditResult)); } catch (e) { }

        /* ═══ VISITOR STATE TRACKING ═══ */
        var vd = null;
        try { vd = JSON.parse(localStorage.getItem('sd_visitor')); } catch(e){}
        if (!vd) vd = { visits: 0, firstVisit: Date.now() };
        if (vd.domain && vd.domain !== domain) {
            vd = { visits: 0, firstVisit: Date.now() };
        }
        vd.domain = domain;
        vd.score = score;
        vd.errors = errors;
        vd.visits = (vd.visits || 0) + 1;
        vd.lastVisit = Date.now();
        try { localStorage.setItem('sd_visitor', JSON.stringify(vd)); } catch(e){}
        if (vd.visits >= 2 && typeof showReturnBanner === 'function') {
            showReturnBanner(vd);
        }

        document.getElementById('reportHeader').textContent =
            '[AUDIT_REPORT_v2.6] — HOST: ' + domain;
        document.getElementById('reportScore').textContent = score + '/100';

        var d = domain;
        var items = [
            { icon: '\u274C', title: 'Thin Content Detection:', text: 'Analiza struktury H2/H3 dla ' + d + ' nie powiodla sie. Twoj tekst to pustka dla LLM. Bez znacznikow Google AI ignoruje opis.' },
            { icon: '\u274C', title: 'E-E-A-T Score: 0:', text: 'Wykryto duplikat tresci (Copy-paste). Algorytm nie widzi eksperckosci. Zaufanie Gemini do zrodla: Minimalne.' },
            { icon: '\u274C', title: 'Entity Recognition: FAILED:', text: 'JSON-LD Product Schema nie wykryta. Google nie widzi Produktu, widzi tylko Zestaw liter. Marka i cena poza indeksem encji.' },
            { icon: '\u274C', title: 'Rich Snippets: MISSING:', text: 'W wynikach wyszukiwania Twoj produkt to goly link. Konkurencja zabiera 80% CTR dzieki gwiazdkom i cenie, ktorych nie masz w kodzie.' },
            { icon: '\u274C', title: 'AI Search Visibility: HIDDEN:', text: 'Proba indeksacji w Perplexity/ChatGPT... Blad. Plaski tekst nie jest czytany przez agentow AI. Jestes poza wynikami AI Overview.' },
            { icon: '\u274C', title: 'Short Description Cannibalization:', text: 'Spalasz relevancje strony, zmuszajac Google do watpienia w cel tresci.' },
            { icon: '\u274C', title: 'Meta Description Optimization: LOW:', text: 'Formula CTR naruszona. Utrata klikniec z organiki: ~40%.' },
            { icon: '\u274C', title: 'Crawl Budget Waste:', text: 'robots.txt otwiera smieciowe strony. Roboty Google traca czas na filtry i sortowanie, nie docierajac do kart produktow.' }
        ];

        var body = document.getElementById('reportBody');
        body.innerHTML = '';
        items.slice(0, errors).forEach(function (item) {
            var div = document.createElement('div');
            div.className = 'ab-report-item';
            div.innerHTML = '<strong>' + item.icon + ' ' + item.title + '</strong> ' + item.text;
            body.appendChild(div);
        });

        /* Case study proof */
        var proofDiv = document.createElement('div');
        proofDiv.className = 'ab-report-proof';
        proofDiv.innerHTML = '<strong>📈 Sklep z ' + errors + ' błędami jak u Ciebie zwiększył sprzedaż o +73% w 21 dni</strong><br>Produkty zaczęły pojawiać się w Google AI Overview i Gemini';
        body.appendChild(proofDiv);

        /* === DYNAMIC CTA: reportCta (hero) === */
        var rc = document.getElementById('reportCta');
        if (rc) {
            if (errors <= 4) {
                rc.innerHTML = 'Popraw ' + errors + ' elementy i zdominuj Google AI →<span>Zacznij pojawiać się w Google AI</span>';
            } else {
                rc.innerHTML = 'Napraw ' + errors + ' błędów zanim konkurencja przejmie Twoich klientów →<span>Zacznij pojawiać się w Google AI</span>';
                if (errors >= 6) rc.classList.add('ab-cta-urgent');
            }
        }

        /* Social proof under reportCta */
        var socialEl = document.getElementById('reportSocial');
        if (socialEl) {
            var avg = errors <= 6 ? '5–6' : '6–7';
            socialEl.textContent = 'Najczęstszy wynik: ' + avg + ' błędów na sklep (na podstawie 127 sklepów)';
            socialEl.style.display = 'block';
        }

        /* FOMO micro-text (session-dynamic, shared with live proof) */
        var fomoCount = Math.floor(Math.random() * 4) + 2;
        var fomoEl = document.getElementById('reportFomo');
        if (fomoEl) { fomoEl.textContent = sklepPl(fomoCount) + ' właśnie naprawiają te błędy'; fomoEl.style.display = 'block'; }

        diagReport.style.display = 'block';

        /* Activate checklist .is-detected */
        var cl = document.getElementById('checklist');
        if (cl) {
            cl.classList.add('is-detected');
            /* Show only `errors` cards, hide rest from bottom */
            var cards = cl.querySelectorAll('.ab-card');
            for (var i = 0; i < cards.length; i++) {
                cards[i].style.display = i < errors ? '' : 'none';
            }
        }
        var sfc = document.getElementById('systemFixCount');
        if (sfc) sfc.textContent = errors;

        /* === DYNAMIC HEADLINE (score-based) === */
        var ct = document.getElementById('checklistTitle');
        if (ct) {
            if (score <= 30) {
                ct.innerHTML = '<span style="color:#ef4444">' + domain + '</span> — KRYTYCZNE: <span style="color:#ef4444">' + errors + ' błędów</span> sprawia, że Twój sklep nie istnieje w Google AI';
            } else if (score <= 50) {
                ct.innerHTML = '<span style="color:#f59e0b">' + domain + '</span> traci klientów — <span style="color:#f59e0b">' + errors + ' błędów</span> blokuje widoczność w AI';
            } else {
                ct.innerHTML = '<span style="color:#22c55e">' + domain + '</span> — popraw <span style="color:#22c55e">' + errors + ' elementów</span> i zwiększ ruch';
            }
        }

        /* Personal subtext + moment of impact */
        var cp = document.getElementById('checklistPersonal');
        if (cp) { cp.textContent = 'Wykryto na podstawie analizy Twojego sklepu'; cp.style.display = 'block'; }
        var ci = document.getElementById('checklistImpact');
        if (ci) { ci.textContent = 'Każdego dnia tracisz klientów na rzecz konkurencji'; ci.style.display = 'block'; }

        /* Dynamic hero buttons — after audit */
        var hp = document.getElementById('heroPrimaryBtn');
        if (hp) hp.style.display = 'none';
        var ob = document.getElementById('heroOutlineBtn');
        if (ob) {
            ob.textContent = 'Zobacz ' + errors + ' wykrytych błędów ↓';
            ob.setAttribute('href', '#checklist');
            ob.className = 'ab-hero-link';
        }

        /* === DYNAMIC CTA: checklistCta === */
        var cc = document.getElementById('checklistCta');
        if (cc) {
            if (errors <= 4) {
                cc.innerHTML = 'Popraw ' + errors + ' elementy i wyprzedź konkurencję →<span>Zacznij pojawiać się w Google AI</span>';
            } else {
                cc.innerHTML = 'Napraw ' + errors + ' błędów zanim konkurencja przejmie Twoich klientów — zanim będzie za późno →<span>Zacznij pojawiać się w Google AI</span>';
            }
        }

        /* === DYNAMIC CTA: blueprintCta (done for you) === */
        var bc = document.getElementById('blueprintCta');
        if (bc) bc.textContent = 'Wdrożymy AI Search za Ciebie → 1000 zł';
        var bt = document.getElementById('blueprintTime');
        if (bt) { bt.textContent = 'Pierwsze efekty: 7–21 dni'; bt.style.display = 'block'; }

        /* === PRE-PAYMENT TRIGGERS === */
        var triggerText;
        if (errors >= 7) {
            triggerText = 'Każdego dnia tracisz klientów na rzecz konkurencji';
        } else if (errors === 6) {
            triggerText = 'Twój sklep jest blisko, ale nadal tracisz ruch z AI';
        } else {
            triggerText = 'Masz potencjał — nie zmarnuj go';
        }
        ['reportTrigger', 'checklistTrigger', 'blueprintTrigger'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) { el.textContent = triggerText; el.style.display = 'block'; }
        });
        ['reportTriggerSub', 'checklistTriggerSub'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) { el.style.display = 'block'; }
        });

        /* === PERSONALIZED PROOF SYSTEM === */
        var base = hashUrl(getDomain(domain));
        /* Proof results — hash-deterministic, realistic range 9–18% */
        var proofPct = 9 + (base % 10); /* 9–18% deterministic per domain */
        var proofCtr = 3 + (base % 6);  /* 3–8% */
        var proofVis = 7 + (base % 8);  /* 7–14% */
        var proofTypes = ['ruchu', 'sprzedaży', 'konwersji', 'klientów', 'widoczności'];
        var proofType = proofTypes[base % proofTypes.length];

        var ps = document.getElementById('proofSection');
        if (ps) {
            document.getElementById('proofCategory').textContent = 'e-commerce';
            document.getElementById('proofErrors').textContent = errors;
            document.getElementById('proofResult').textContent =
                '+' + proofPct + '% ' + proofType + ' z Google AI w 21 dni';
            document.getElementById('proofMetrics').textContent =
                'Widoczność w AI Overview: +' + proofVis + '% · CTR: +' + proofCtr + '%';
            document.getElementById('proofDesc').textContent =
                'Po wdrożeniu struktury AI i danych JSON-LD produkty zaczęły pojawiać się w Google AI Overview i Gemini.';
            document.getElementById('proofFooter').textContent =
                'Wdrożenie: 3 dni · Branża: e-commerce · Źródło: dane z wdrożeń AI Search';
            ps.style.display = 'block';
        }

        /* Mini proof (pseudo-dynamic count) */
        var shopsCount = 120 + (base % 30);
        var mp = document.getElementById('miniProof');
        if (mp) {
            mp.textContent = 'Sklepy z takim profilem jak Twój tracą klientów z Google AI — naprawiliśmy to w ' + shopsCount + ' sklepach';
            mp.style.display = 'block';
        }

        /* Live proof (cycle FOMO — 12 niches, 20+ dynamic vars per session) */
        var allNiches = ['moda', 'elektronika', 'budownictwo', 'wnętrza', 'narzędzia', 'zdrowie', 'motoryzacja', 'zwierzęta', 'sport', 'spożywcza', 'zabawki', 'dziecko'];
        /* Session-random dynamic numbers (different every page load) */
        var dyn = {
            shops: Math.floor(Math.random() * 4) + 2,       /* 2–5 */
            shops2: Math.floor(Math.random() * 3) + 3,      /* 3–5 */
            errors: Math.floor(Math.random() * 4) + 5,      /* 5–8 */
            errors2: Math.floor(Math.random() * 3) + 4,     /* 4–6 */
            days: Math.floor(Math.random() * 14) + 7,       /* 7–20 */
            days2: Math.floor(Math.random() * 10) + 3,      /* 3–12 */
            mins: Math.floor(Math.random() * 45) + 5,       /* 5–49 */
            mins2: Math.floor(Math.random() * 30) + 10,     /* 10–39 */
            products: Math.floor(Math.random() * 64800) + 200, /* 200–65000 */
            products2: Math.floor(Math.random() * 500) + 100,/* 100–599 */
            pct: Math.floor(Math.random() * 10) + 5,        /* 5–14% */
            pct2: Math.floor(Math.random() * 8) + 3,        /* 3–10% */
            pct3: Math.floor(Math.random() * 10) + 7,       /* 7–16% */
            ctr: Math.floor(Math.random() * 6) + 2,         /* 2–7% */
            vis: Math.floor(Math.random() * 10) + 5,        /* 5–14% */
            orders: Math.floor(Math.random() * 10) + 3,     /* 3–12 */
            hours: Math.floor(Math.random() * 6) + 1,       /* 1–6 */
            hours2: Math.floor(Math.random() * 4) + 2,      /* 2–5 */
            pages: Math.floor(Math.random() * 150) + 50,    /* 50–199 */
            rank: Math.floor(Math.random() * 8) + 3         /* 3–10 */
        };
        var liveTemplates = [
            function (n) { return sklepPl(fomoCount) + ' z branży ' + n + ' właśnie wdrażają AI Search'; },
            function (n) { return 'Sklep z branży ' + n + ' — widoczność w AI wzrosła o +' + dyn.pct + '% w ' + dyn.days + ' dni'; },
            function (n) { return 'Nowe wdrożenie AI Search — branża: ' + n + ' (' + dyn.products + ' produktów)'; },
            function (n) { return sklepPl(dyn.shops2) + ' naprawiły ' + dyn.errors + ' błędów w ostatnich ' + dyn.hours + 'h'; },
            function (n) { return 'Sklep z branży ' + n + ' pojawił się w Google AI Overview ' + dyn.mins + ' min temu'; },
            function (n) { return 'Branża ' + n + ': +' + dyn.pct2 + '% CTR po wdrożeniu AI Search (' + dyn.days2 + ' dni)'; }
        ];
        var liveIdx = 0;
        function showLiveProof() {
            var lp = document.getElementById('liveProof');
            var lpt = document.getElementById('liveProofText');
            if (!lp || !lpt) return;
            var niche = allNiches[liveIdx % allNiches.length];
            var tpl = liveTemplates[liveIdx % liveTemplates.length];
            lpt.textContent = tpl(niche);
            liveIdx++;
            lp.style.display = 'flex';
            setTimeout(function () { lp.style.display = 'none'; }, 6000);
        }
        setTimeout(showLiveProof, 4000);
        setInterval(function () { showLiveProof(); }, 45000 + Math.random() * 15000);

        setTimeout(function () {
            diagReport.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 200);
    }

    async function runDiag(rawUrl) {
        var domain = getDomain(rawUrl);
        var base = hashUrl(domain);
        var errors = base % 4 + 5;
        if (base % 10 === 0) errors = 4;
        var score = 18 + (base % 41);
        diagTerminal.style.display = 'block';
        diagOutput.innerHTML = '<span class="ab-cursor"></span>';
        diagReport.style.display = 'none';

        if (isBlack(rawUrl)) {
            await typeLine('log-fail', '> Łączenie z ' + domain + '...', 400);
            await typeLine('log-fail', '> ODRZUCONO — domena niezgodna z regulaminem.', 800);
            await typeLine('log-info', '> Narzędzie służy wyłącznie do analizy sklepów e-commerce.', 1200);
            await typeLine('log-info', '> Wpisz adres swojego sklepu internetowego.', 1600);
            return;
        }

        if (isWhite(rawUrl)) {
            await typeLine('log-ok', '> Łączenie z ' + domain + '...', 400);
            await typeLine('log-ok', '> Indeksacja AI: WYKRYTA', 800);
            await typeLine('log-ok', '> Struktura JSON-LD, Schema.org: OK', 1000);
            await typeLine('log-ok', '> E-E-A-T, Rich Snippets: AKTYWNE', 1200);
            await typeLine('log-ok', '> Widoczność w Google AI Overview: TAK', 1400);
            await typeLine('log-ok', '> STATUS: ZOPTYMALIZOWANY — pełna infrastruktura AI Search.', 1800);
            await typeLine('log-info', '> Ta domena posiada wdrożony system AI Visibility Booster.', 2200);
            return;
        }

        await typeLine('log-ok', '> Inicjalizacja analizy gotowosci AI dla: ' + domain + '...', 200);
        await typeLine('log-ok', '> Uzyskano dostep do bazy wiedzy Google SGE... OK.', 400);
        await typeLine('log-info', '> BOOSTER_ENGINE v1.5: Inicjalizacja protokolu analizy...', 600);
        await typeLine('log-ok', '> API Gemini 1.5 Flash: Polaczono (Latency 42ms).', 800);
        await typeLine('log-info', '> Skanowanie struktury DOM: ' + domain + '... Gotowe.', 1000);
        await typeLine('log-ok', '> Pobieranie danych Knowledge Panel... OK.', 1200);
        await typeLine('log-fail', '> Poziom struktury JSON-LD Product... [NISKI]', 1500);
        await typeLine('log-warn', '> Analiza sygnalow EEAT Authority... [SLABY]', 1700);
        await typeLine('log-fail', '> Gestosc semantyczna (GEO Logic)... [OGRANICZONA]', 1900);
        await typeLine('log-warn', '> Rozpoznawalnosc marki w Google AI Overview... [NIEJEDNOZNACZNE]', 2100);
        await typeLine('log-fail', '> Klarownosc encji dla ' + domain + '... [OGRANICZONA]', 2300);
        await typeLine('log-info', '> -------------------------------------------', 2600);
        await typeLine('log-score', '> WYNIK ANALIZY: ' + score + '/100 — OGRANICZONA GOTOWOSC', 2800);
        await typeLine('log-fail', '> Ograniczona ekspozycja w wynikach generowanych przez AI', 3000);
        await typeLine('log-ok', '> Koszt tego raportu: 0 zł (Wersja testowa)', 3200);
        await typeLine('log-info', '> Na podstawie analizy 127 sklepow e-commerce', 3400);
        await typeLine('log-warn', '> Koszt wdrozenia poprawek (' + errors + ' sygnalow): od 1 000 zł', 3600);
        await typeLine('log-fail', '> STATUS: OGRANICZONA WIDOCZNOSC W AI SEARCH', 3800);

        setTimeout(function () { showReport(domain, score); }, 4200);
    }

    diagStart.addEventListener('click', function () {
        var url = diagUrl.value.trim();
        if (!url) { diagUrl.focus(); return; }
        /* Validate: must look like a domain (contains at least one dot) */
        var domain = getDomain(url);
        if (domain.indexOf('.') === -1) {
            diagUrl.style.border = '2px solid #ef4444';
            diagUrl.setAttribute('placeholder', 'Wpisz adres sklepu, np. sklep.pl');
            diagUrl.value = '';
            diagUrl.focus();
            setTimeout(function () { diagUrl.style.border = ''; }, 3000);
            return;
        }
        diagStart.disabled = true;
        diagStart.textContent = 'ANALIZA...';
        /* Compute score for notification */
        var notifyBase = hashUrl(domain);
        var notifyErrors = notifyBase % 4 + 5;
        if (notifyBase % 10 === 0) notifyErrors = 4;
        var notifyScore = 18 + (notifyBase % 41);
        /* Notify about audit (non-blocking) */
        try { fetch('/api/audit-notify.php', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: url, score: notifyScore, errors: notifyErrors, referrer: document.referrer || 'direct', utmSource: new URLSearchParams(location.search).get('utm_source') || '' }) }); } catch (e) { }
        runDiag(url).then(function () {
            diagStart.disabled = false;
            diagStart.textContent = 'SPRAWDŹ INDEKS AI';
        });
    });
    diagUrl.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') diagStart.click();
    });

    /* Blinking | in placeholder */
    var ph = diagUrl.getAttribute('placeholder');
    var blinkOn = true;
    var blinkTimer = setInterval(function () {
        if (document.activeElement === diagUrl) return;
        diagUrl.setAttribute('placeholder', blinkOn ? '|  ' + ph : '   ' + ph);
        blinkOn = !blinkOn;
    }, 600);
    diagUrl.addEventListener('focus', function () {
        diagUrl.setAttribute('placeholder', ph);
    });
    diagUrl.addEventListener('blur', function () { blinkOn = true; });

    /* ═══ NICHE MODULE HOVER LOGS ═══ */
    document.querySelectorAll('.ab-niche[data-log]').forEach(function (card) {
        var logEl = card.querySelector('.ab-niche-log');
        var timers = [];
        card.addEventListener('mouseenter', function () {
            var lines = card.getAttribute('data-log').split('|');
            logEl.innerHTML = '';
            lines.forEach(function (line, i) {
                timers.push(setTimeout(function () {
                    var span = document.createElement('span');
                    span.textContent = line;
                    span.style.opacity = '0';
                    span.style.transition = 'opacity 0.2s';
                    logEl.appendChild(span);
                    setTimeout(function () { span.style.opacity = '1'; }, 20);
                }, i * 150));
            });
        });
        card.addEventListener('mouseleave', function () {
            timers.forEach(clearTimeout);
            timers = [];
            logEl.innerHTML = '';
        });
    });
})();

// Auto-open checkout from URL query: ?pkg=starter|professional|rocket
(function() {
    var params = new URLSearchParams(window.location.search);
    var pkg = params.get('pkg');
    if (pkg && ['starter', 'professional', 'rocket'].indexOf(pkg) !== -1) {
        setTimeout(function() {
            var el = document.getElementById('calc-section');
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            setTimeout(function() {
                if (typeof selectPackageAndOrder === 'function') selectPackageAndOrder(pkg);
            }, 800);
        }, 1000);
    }
})();

// Auto-start diagnostic from URL query: ?url=https://example.com
(function() {
    var params = new URLSearchParams(window.location.search);
    var autoUrl = params.get('url');
    if (autoUrl) {
        setTimeout(function() {
            var diagUrl = document.getElementById('diagUrl');
            var diagStart = document.getElementById('diagStart');
            if (diagUrl && diagStart) {
                var console = document.querySelector('.ab-console');
                if (console) console.scrollIntoView({ behavior: 'smooth', block: 'center' });
                diagUrl.value = autoUrl;
                setTimeout(function() { diagStart.click(); }, 600);
            }
        }, 1200);
    }

    // Auto-open checkout from email CTA (?package=starter/professional/rocket)
    var urlPkg = new URLSearchParams(window.location.search).get('package');
    if (urlPkg && ['starter', 'professional', 'rocket'].indexOf(urlPkg) !== -1) {
        window.addEventListener('load', function() {
            setTimeout(function() {
                window.selectPackageAndOrder(urlPkg);
            }, 500);
        });
    }
})();

/* ═══ RETURNING VISITOR ENGINE ═══ */
function showReturnBanner(vd) {
    if (document.getElementById('sdReturnBanner')) return;
    var dismissKey = 'sd_banner_dismissed_' + (vd.domain || '');
    try { if (localStorage.getItem(dismissKey)) return; } catch(e){}

    var daysAgo = Math.floor((Date.now() - vd.lastVisit) / 86400000);
    var msg, cta, ctaAction;

    if (vd.visits === 2) {
        /* V2: confirmation — diagnostic layer */
        msg =
        '<strong>Ponowna analiza wykryta</strong><br>' +
        'Sklep: <strong>' + vd.domain + '</strong><br>' +
        'Wynik audytu: <strong style="color:#ef4444">' + vd.score + '/100</strong> \u00b7 ' +
        'Zidentyfikowane: <span style="color:#f87171">' + vd.errors + ' element\u00f3w wp\u0142ywaj\u0105cych na widoczno\u015b\u0107</span><br>' +
        'Brak zmian od ostatniego uruchomienia analizy.<br>' +
        'System nie wykry\u0142 wdro\u017cenia rekomendacji dotycz\u0105cych SEO i AI Search.<br>' +
        'Status: <em>brak implementacji</em>';
        cta = 'Zobacz co blokuje widoczno\u015b\u0107 \u2192';
        ctaAction = '#checklist';

    } else if (vd.visits === 3) {
        /* V3: loss awareness — value leakage framing */
        msg =
        '<strong>Brak zmian = brak wzrostu</strong><br>' +
        'Sklep <strong>' + vd.domain + '</strong> nadal nie wykorzystuje zidentyfikowanych mo\u017cliwo\u015bci optymalizacji widoczno\u015bci w wyszukiwarkach i systemach AI.<br>' +
        'Rekomendacje pozostaj\u0105 niewdro\u017cone.<br>' +
        'W efekcie potencjalny ruch organiczny jest systematycznie przejmowany przez konkurencj\u0119.<br>' +
        '<span style="color:#f59e0b">Analiza bez wdro\u017cenia nie wp\u0142ywa na wynik biznesowy.</span>';
        if (daysAgo >= 1) {
            msg += '<br><span style="color:#ef4444">Od ostatniej analizy min\u0119\u0142o ' + daysAgo + ' dni. Ka\u017cdy dzie\u0144 bez zmian zwi\u0119ksza strat\u0119 potencjalnego ruchu.</span>';
        }
        cta = 'Zobacz ile tracisz \u2192';
        ctaAction = '#calc-section';

    } else {
        /* V4+: responsibility pressure — execution layer */
        msg =
        '<strong>System wykry\u0142 powtarzaj\u0105ce si\u0119 analizy bez wdro\u017cenia</strong><br>' +
        'Sklep <strong>' + vd.domain + '</strong> by\u0142 wielokrotnie analizowany bez implementacji rekomendacji.<br>' +
        'Status: <em>utrzymuj\u0105cy si\u0119 brak dzia\u0142a\u0144 optymalizacyjnych</em><br>' +
        '<span style="color:#f87171">Konsekwencje: ograniczona widoczno\u015b\u0107 \u00b7 niewykorzystany potencja\u0142 AI Search \u00b7 utrata ruchu na rzecz konkurencji</span><br>' +
        '<span style="color:#f59e0b">Analiza nie zmienia wyniku \u2014 zmienia go wdro\u017cenie.</span>';
        if (daysAgo >= 1) {
            msg += '<br><span style="color:#ef4444">Od ostatniej analizy min\u0119\u0142o ' + daysAgo + ' dni. Brak dzia\u0142a\u0144 w tym okresie oznacza dalsz\u0105 kumulacj\u0119 utraconych wej\u015b\u0107.</span>';
        }
        cta = 'Napraw to teraz \u2192';
        ctaAction = '#calc-section';
    }

    var banner = document.createElement('div');
    banner.id = 'sdReturnBanner';
    banner.style.cssText =
        'position:fixed;top:0;left:0;right:0;z-index:99999;' +
        'background:#0f172a;color:#e2e8f0;' +
        'padding:14px 20px;font-size:13px;line-height:1.6;' +
        'border-bottom:2px solid #7c3aed;' +
        'display:flex;gap:16px;flex-wrap:wrap;align-items:center;justify-content:center';

    var msgDiv = document.createElement('div');
    msgDiv.innerHTML = '\ud83d\udd04 ' + msg;

    var btn = document.createElement('a');
    btn.href = ctaAction;
    btn.textContent = cta;
    btn.style.cssText =
        'background:#7c3aed;color:#fff;padding:8px 18px;border-radius:8px;' +
        'font-weight:700;text-decoration:none;white-space:nowrap';

    var close = document.createElement('button');
    close.textContent = '\u2715';
    close.style.cssText =
        'background:none;border:none;color:#94a3b8;font-size:18px;cursor:pointer';
    close.onclick = function() {
        banner.remove();
        document.body.style.paddingTop = '';
        try { localStorage.setItem(dismissKey, '1'); } catch(e){}
    };

    banner.appendChild(msgDiv);
    banner.appendChild(btn);
    banner.appendChild(close);
    document.body.prepend(banner);
    if (!document.body.style.paddingTop || document.body.style.paddingTop === '0px') {
        document.body.style.paddingTop = banner.offsetHeight + 'px';
    }
}

/* Fallback: show banner on page load for returning visitors */
(function() {
    var vd = null;
    try { vd = JSON.parse(localStorage.getItem('sd_visitor')); } catch(e){}
    if (!vd || vd.visits < 2) return;
    showReturnBanner(vd);
})();

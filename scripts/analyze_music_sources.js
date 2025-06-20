const { firefox } = require('playwright');

async function analyzeMusicSources() {
  const browser = await firefox.launch({ 
    headless: true,
    args: ['--no-sandbox'] 
  });
  
  const sources = [
    {
      url: 'https://kodi.wiki/view/Scraping_Music',
      name: 'Kodi Music Scraping'
    },
    {
      url: 'https://medium.com/@stephaniecaress/scraping-pitchforks-best-new-music-be563d18ea4f',
      name: 'Pitchfork Scraping'
    },
    {
      url: 'https://tilburgsciencehub.com/blog/musictoscrape',
      name: 'MusicToScrape'
    },
    {
      url: 'https://python.plainenglish.io/discover-new-music-by-scraping-the-web-with-python-9caa04f4bf41',
      name: 'Python Music Discovery'
    },
    {
      url: 'https://github.com/LF3551/Apple-Music-Playlist-Scraper',
      name: 'Apple Music Playlist Scraper'
    },
    {
      url: 'https://forum.kodi.tv/showthread.php?tid=264719',
      name: 'Kodi Forum Thread'
    }
  ];
  
  const results = {};
  
  for (const source of sources) {
    console.log(`\nAnalyzing: ${source.name}`);
    console.log('=' .repeat(50));
    
    try {
      const page = await browser.newPage();
      await page.goto(source.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      
      // Extract main content
      const content = await page.evaluate(() => {
        // Try various content selectors
        const selectors = [
          'article', 
          'main', 
          '.content', 
          '.post-content',
          '.readme-article',
          '#content',
          '.markdown-body',
          '.post',
          '.entry-content'
        ];
        
        for (const selector of selectors) {
          const element = document.querySelector(selector);
          if (element) {
            return element.innerText;
          }
        }
        
        // Fallback to body
        return document.body.innerText;
      });
      
      // Extract key information
      const keyInfo = await page.evaluate(() => {
        const info = {
          title: document.title,
          headings: [],
          codeBlocks: [],
          links: []
        };
        
        // Get headings
        document.querySelectorAll('h1, h2, h3').forEach(h => {
          info.headings.push(h.innerText);
        });
        
        // Get code blocks
        document.querySelectorAll('pre, code').forEach(code => {
          const text = code.innerText;
          if (text.length > 50) { // Skip small inline code
            info.codeBlocks.push(text.substring(0, 200) + '...');
          }
        });
        
        // Get relevant links
        document.querySelectorAll('a').forEach(link => {
          const href = link.href;
          const text = link.innerText;
          if (href && (href.includes('api') || href.includes('github') || 
                      href.includes('music') || href.includes('scrape'))) {
            info.links.push({ text, href });
          }
        });
        
        return info;
      });
      
      results[source.name] = {
        url: source.url,
        success: true,
        contentLength: content.length,
        keyInfo,
        contentSnippet: content.substring(0, 500)
      };
      
      await page.close();
      
    } catch (error) {
      results[source.name] = {
        url: source.url,
        success: false,
        error: error.message
      };
    }
  }
  
  await browser.close();
  
  // Save results
  require('fs').writeFileSync(
    '/home/mik/SEARXNG/searxng-cool/docs/music-engines/analyzed_sources.json',
    JSON.stringify(results, null, 2)
  );
  
  // Print summary
  console.log('\n\nSUMMARY');
  console.log('=' .repeat(50));
  
  for (const [name, result] of Object.entries(results)) {
    if (result.success) {
      console.log(`✓ ${name}: ${result.keyInfo.headings.length} headings, ${result.keyInfo.codeBlocks.length} code blocks`);
    } else {
      console.log(`✗ ${name}: ${result.error}`);
    }
  }
}

analyzeMusicSources().catch(console.error);
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
chromium.use(StealthPlugin());
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";

const COOKIE_DIR = "cookies";
const TEMPLATES_FILE = "notary_templates.json";
const CONTACTS_FILE = "notary_contacts.json";

// California zipcodes sampled strategically across major metro areas
const CA_ZIPS = ["90001","90010","90012","90024","90025","90034","90036","90045","90049",
  "90056","90064","90066","90069","90094","90201","90210","90211","90212","90220","90230",
  "90240","90245","90247","90250","90254","90255","90260","90262","90263","90265","90266",
  "90272","90274","90275","90277","90278","90280","90291","90292","90293","90301","90302",
  "90304","90305","90401","90403","90404","90405","90501","90502","90503","90504","90505",
  "90601","90620","90621","90623","90630","90631","90638","90640","90650","90660","90670",
  "90701","90703","90706","90710","90712","90713","90715","90716","90717","90720","90723",
  "90731","90732","90740","90744","90745","90746","90755","90802","90803","90804","90805",
  "90806","90807","90808","90810","90813","90814","90815","91001","91006","91007","91008",
  "91010","91011","91016","91020","91024","91030","91040","91042","91101","91103","91104",
  "91105","91106","91107","91108","91201","91202","91203","91204","91205","91206","91207",
  "91208","91214","91301","91302","91303","91304","91306","91307","91311","91316","91320",
  "91321","91324","91325","91326","91330","91331","91335","91340","91342","91343","91344",
  "91345","91350","91351","91352","91354","91355","91356","91360","91361","91362","91364",
  "91367","91371","91377","91381","91384","91387","91390","91401","91402","91403","91405",
  "91406","91411","91423","91501","91502","91504","91505","91506","91601","91602","91604",
  "91605","91606","91607","91608","91701","91702","91706","91708","91709","91710","91711",
  "91722","91723","91724","91730","91731","91732","91733","91737","91739","91740","91741",
  "91744","91745","91746","91748","91750","91752","91754","91755","91759","91761","91762",
  "91763","91764","91765","91766","91767","91768","91770","91773","91775","91776","91780",
  "91784","91786","91789","91790","91791","91792","91801","91803","91901","91902","91905",
  "91910","91911","91913","91914","91915","91932","91935","91941","91942","91945","91950",
  "91962","91977","92003","92007","92008","92009","92010","92011","92014","92019","92020",
  "92021","92024","92025","92026","92027","92028","92029","92037","92040","92054","92055",
  "92056","92057","92058","92061","92064","92065","92067","92069","92071","92075","92078",
  "92081","92082","92083","92084","92101","92102","92103","92104","92105","92106","92107",
  "92108","92109","92110","92111","92113","92114","92115","92116","92117","92118","92119",
  "92120","92121","92122","92123","92124","92126","92127","92128","92129","92130","92131",
  "92139","92145","92147","92154","92173","92201","92210","92220","92223","92225","92227",
  "92231","92233","92234","92236","92240","92241","92242","92243","92253","92254","92260",
  "92264","92270","92273","92274","92276","92277","92282","92283","92284","92301","92307",
  "92308","92311","92314","92315","92316","92320","92324","92325","92335","92336","92337",
  "92344","92345","92346","92354","92356","92358","92359","92368","92371","92372","92373",
  "92374","92375","92376","92377","92382","92391","92392","92394","92395","92397","92399",
  "92401","92404","92405","92407","92408","92410","92411","92501","92503","92504","92505",
  "92506","92507","92508","92509","92530","92532","92536","92543","92544","92545","92548",
  "92549","92551","92553","92555","92557","92562","92563","92567","92570","92571","92582",
  "92583","92584","92585","92587","92590","92591","92592","92595","92596","92602","92603",
  "92604","92606","92607","92610","92612","92614","92617","92618","92620","92624","92625",
  "92626","92627","92629","92630","92637","92646","92647","92648","92649","92651","92653",
  "92655","92656","92657","92660","92661","92662","92663","92672","92673","92675","92676",
  "92677","92678","92679","92683","92688","92691","92692","92694","92701","92703","92704",
  "92705","92706","92707","92708","92780","92782","92801","92802","92804","92805","92806",
  "92807","92808","92821","92831","92832","92833","92835","92840","92841","92843","92844",
  "92845","92860","92861","92865","92866","92867","92868","92869","92870","92879","92880",
  "92881","92882","92883","92886","92887","93001","93003","93004","93010","93012","93013",
  "93015","93021","93022","93023","93030","93033","93035","93036","93040","93041","93060",
  "93063","93064","93065","93066","93067","93101","93103","93105","93108","93109","93110",
  "93111","93117","93201","93202","93203","93205","93206","93207","93208","93210","93212",
  "93215","93218","93219","93220","93221","93222","93223","93224","93225","93226","93230",
  "93234","93235","93238","93239","93240","93241","93242","93243","93244","93245","93247",
  "93249","93250","93251","93252","93254","93255","93256","93257","93258","93260","93261",
  "93263","93265","93266","93267","93268","93270","93271","93272","93274","93276","93277",
  "93280","93285","93286","93287","93291","93292","93301","93304","93305","93306","93307",
  "93308","93309","93311","93312","93313","93314","93401","93402","93405","93420","93422",
  "93424","93426","93427","93428","93429","93430","93432","93433","93434","93436","93437",
  "93440","93441","93442","93444","93445","93446","93449","93450","93451","93452","93453",
  "93454","93455","93458","93460","93461","93463","93465","93501","93505","93510","93512",
  "93514","93516","93518","93522","93523","93524","93526","93527","93528","93529","93530",
  "93531","93532","93534","93535","93536","93543","93544","93545","93546","93549","93550",
  "93551","93552","93553","93554","93555","93558","93560","93561","93562","93563","93591",
  "93592","93596","93601","93602","93603","93604","93605","93606","93607","93608","93609",
  "93610","93611","93612","93613","93614","93615","93616","93618","93619","93620","93621",
  "93622","93623","93624","93625","93626","93627","93628","93630","93631","93633","93634",
  "93635","93636","93637","93638","93640","93641","93642","93643","93644","93645","93646",
  "93647","93648","93649","93650","93651","93652","93653","93654","93656","93657","93660",
  "93661","93662","93664","93665","93666","93667","93668","93669","93670","93673","93675",
  "93701","93702","93703","93704","93705","93706","93710","93711","93720","93721","93722",
  "93723","93725","93726","93727","93728","93730","93740","93901","93905","93906","93907",
  "93908","93920","93921","93923","93924","93925","93926","93927","93928","93930","93932",
  "93933","93940","93950","93953","93954","93955","93960","94002","94005","94010","94014",
  "94015","94019","94020","94021","94022","94024","94025","94027","94028","94030","94037",
  "94038","94040","94041","94043","94044","94060","94061","94062","94063","94065","94066",
  "94070","94080","94085","94086","94087","94089","94102","94103","94104","94105","94107",
  "94108","94109","94110","94111","94112","94114","94115","94116","94117","94118","94121",
  "94122","94123","94124","94127","94128","94129","94130","94131","94132","94133","94134",
  "94158","94301","94303","94304","94305","94306","94401","94402","94403","94404","94501",
  "94502","94505","94506","94507","94508","94509","94510","94512","94513","94514","94515",
  "94516","94517","94518","94519","94520","94521","94523","94525","94526","94528","94530",
  "94531","94533","94534","94535","94536","94538","94539","94541","94542","94544","94545",
  "94546","94547","94548","94549","94550","94551","94552","94553","94555","94556","94558",
  "94559","94560","94561","94562","94563","94564","94565","94566","94567","94568","94569",
  "94571","94572","94573","94574","94575","94576","94577","94578","94579","94580","94582",
  "94583","94585","94586","94587","94588","94589","94590","94591","94592","94595","94596",
  "94597","94598","94599","94601","94602","94603","94605","94606","94607","94608","94609",
  "94610","94611","94612","94613","94618","94619","94621","94702","94703","94704","94705",
  "94706","94707","94708","94709","94710","94720","94801","94803","94804","94805","94806",
  "94901","94903","94904","94920","94922","94923","94924","94925","94928","94929","94930",
  "94931","94933","94937","94938","94939","94940","94941","94945","94946","94947","94949",
  "94950","94951","94952","94953","94954","94955","94956","94957","94960","94963","94964",
  "94965","94970","94971","94972","94973","94974","95001","95002","95003","95004","95005",
  "95006","95007","95008","95010","95012","95013","95014","95017","95018","95019","95020",
  "95023","95030","95032","95033","95035","95036","95037","95039","95041","95042","95043",
  "95045","95046","95050","95051","95053","95054","95056","95060","95062","95064","95065",
  "95066","95070","95073","95075","95076","95077","95106","95110","95111","95112","95113",
  "95116","95117","95118","95119","95120","95121","95122","95123","95124","95125","95126",
  "95127","95128","95129","95130","95131","95132","95133","95134","95135","95136","95138",
  "95139","95140","95148","95202","95203","95204","95205","95206","95207","95209","95210",
  "95211","95212","95215","95219","95220","95222","95223","95224","95225","95226","95227",
  "95228","95230","95231","95232","95233","95234","95236","95237","95240","95242","95245",
  "95246","95247","95248","95249","95250","95251","95252","95253","95254","95255","95257",
  "95258","95301","95303","95304","95305","95306","95307","95309","95310","95311","95312",
  "95313","95314","95315","95316","95317","95318","95319","95320","95321","95322","95323",
  "95324","95325","95326","95327","95328","95329","95330","95333","95334","95335","95336",
  "95337","95338","95340","95341","95342","95343","95344","95345","95346","95347","95348",
  "95350","95351","95354","95355","95356","95357","95358","95360","95361","95363","95364",
  "95365","95366","95367","95368","95369","95370","95372","95374","95375","95376","95377",
  "95379","95380","95381","95382","95383","95385","95386","95387","95388","95389","95391",
  "95401","95403","95404","95405","95406","95407","95409","95410","95412","95415","95416",
  "95417","95418","95420","95421","95422","95423","95425","95427","95428","95429","95430",
  "95431","95432","95435","95436","95437","95439","95441","95442","95443","95444","95445",
  "95446","95448","95449","95450","95451","95452","95453","95454","95456","95457","95458",
  "95459","95460","95461","95462","95463","95464","95465","95466","95467","95468","95469",
  "95470","95471","95472","95476","95482","95485","95486","95487","95488","95490","95492",
  "95493","95494","95497","95501","95503","95511","95514","95519","95521","95524","95525",
  "95526","95527","95528","95531","95536","95537","95540","95543","95546","95547","95548",
  "95549","95551","95552","95553","95554","95555","95556","95558","95559","95560","95562",
  "95563","95564","95565","95567","95568","95569","95570","95571","95573","95585","95587",
  "95589","95595","95601","95602","95603","95604","95605","95606","95607","95608","95610",
  "95612","95614","95615","95616","95618","95619","95620","95621","95623","95624","95625",
  "95626","95627","95628","95629","95630","95631","95632","95633","95634","95635","95636",
  "95638","95639","95640","95641","95642","95645","95646","95648","95650","95651","95652",
  "95653","95655","95656","95658","95659","95660","95661","95662","95663","95664","95665",
  "95666","95667","95668","95669","95670","95672","95673","95674","95675","95677","95678",
  "95679","95680","95681","95682","95683","95684","95685","95686","95687","95688","95689",
  "95690","95691","95692","95693","95694","95695","95697","95698","95699","95701","95703",
  "95709","95713","95714","95715","95717","95720","95721","95722","95726","95728","95735",
  "95736","95742","95746","95747","95757","95758","95762","95765","95776","95811","95814",
  "95815","95816","95817","95818","95819","95820","95821","95822","95823","95824","95825",
  "95826","95827","95828","95829","95830","95831","95832","95833","95834","95835","95836",
  "95837","95838","95840","95841","95842","95843","95864","95901","95903","95910","95912",
  "95914","95915","95916","95917","95918","95919","95920","95922","95923","95925","95926",
  "95928","95930","95932","95934","95935","95936","95937","95938","95939","95941","95942",
  "95943","95944","95945","95946","95947","95948","95949","95950","95951","95953","95954",
  "95955","95956","95957","95959","95960","95961","95962","95963","95965","95966","95968",
  "95969","95970","95971","95972","95973","95974","95975","95977","95978","95979","95981",
  "95982","95983","95984","95986","95987","95988","95991","96001","96002","96003","96006",
  "96007","96008","96009","96010","96011","96013","96014","96015","96016","96017","96019",
  "96020","96021","96022","96023","96024","96025","96027","96028","96029","96031","96032",
  "96033","96034","96035","96037","96038","96039","96040","96041","96044","96046","96047",
  "96048","96049","96050","96051","96052","96054","96055","96056","96057","96058","96059",
  "96061","96062","96063","96064","96065","96067","96068","96069","96071","96073","96074",
  "96075","96076","96078","96079","96080","96084","96085","96086","96087","96088","96089",
  "96090","96091","96092","96093","96094","96095","96096","96097","96101","96103","96104",
  "96105","96106","96107","96108","96109","96110","96111","96112","96113","96114","96115",
  "96116","96117","96118","96119","96120","96121","96122","96123","96124","96125","96126",
  "96127","96128","96129","96130","96132","96133","96134","96135","96136","96137","96140",
  "96141","96142","96143","96145","96146","96148","96150","96151","96152","96154","96155",
  "96156","96157","96158","96160","96161","96162"];

const SITES = {
  notarycafe: {
    name: "Notary Cafe",
    baseUrl: "https://www.notarycafe.com",
    loginUrl: "/account/logon",
    registerUrl: "/register",
    searchUrl: "/find-a-notary",
    profilePath: "/profile",
    features: ["register", "login", "search", "profile", "message"],
    selectors: {
      login: { username: 'input[name="UserName"]', password: 'input[name="Password"]', submit: 'button:has-text("Log In"), input[type="submit"]' },
      register: { firstName: 'input[placeholder="First Name"]', lastName: 'input[placeholder="Last Name"]', email: 'input[placeholder="Email"]', password: 'input[placeholder="Password"]', confirmPass: 'input[placeholder="Confirm Password"]', workPhone: 'input[placeholder="Work Number"]', street: 'input[placeholder="Street Adress"]', city: 'input[placeholder="City"]', zip: 'input[placeholder="Zip"]', state: "select", submit: 'button:has-text("Register")' },
      search: { input: "#SearchString" },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' },
      message: { button: 'a[href*="message"], button:has-text("Message")', textarea: "textarea, [contenteditable='true']", send: 'button[type="submit"], button:has-text("Send")' }
    }
  },

  notaryjane: {
    name: "Notary Jane",
    baseUrl: "https://notaryjane.com",
    loginUrl: "/login",
    registerUrl: "/register",
    searchUrl: "/search",
    features: ["login", "register", "search", "profile"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[name="search"], input[placeholder*="search"]' },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' },
      message: { button: 'a[href*="message"], button:has-text("Message")', textarea: "textarea, [contenteditable='true']", send: 'button[type="submit"], button:has-text("Send")' }
    }
  },

  mobilenotarynet: {
    name: "MobileNotaryNet",
    baseUrl: "https://mobilenotarynet.com",
    loginUrl: "/login",
    registerUrl: "/register",
    searchUrl: "/notary-search",
    features: ["login", "register", "search", "profile"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[placeholder*="search"], input[name="search"]' },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' },
      message: { button: 'a[href*="message"], button:has-text("Message")', textarea: "textarea, [contenteditable='true']", send: 'button[type="submit"], button:has-text("Send")' }
    }
  },

  gotary: {
    name: "GOTARY",
    baseUrl: "https://www.gotary.com",
    loginUrl: "/account",
    registerUrl: "/account/register",
    searchUrl: "/notaries",
    features: ["login", "register", "search", "profile"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[name="search"], input[placeholder*="search"]' },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' },
      message: { button: 'a[href*="message"], button:has-text("Message")', textarea: "textarea, [contenteditable='true']", send: 'button[type="submit"], button:has-text("Send")' }
    }
  },

  notarylocate: {
    name: "Notary Locate",
    baseUrl: "https://www.notarylocate.com",
    loginUrl: "/login",
    registerUrl: "/register",
    searchUrl: "/search",
    features: ["login", "register", "search"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[placeholder*="search"], input[name="search"]' }
    }
  },

  notarywide: {
    name: "NotaryWide",
    baseUrl: "https://notarywide.com",
    loginUrl: "/login",
    registerUrl: "/register",
    searchUrl: "/notaries",
    features: ["login", "register", "search", "profile"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[placeholder*="search"], input[name="search"]' },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' }
    }
  },

  onlinenotarydirectory: {
    name: "Online Notary Directory",
    baseUrl: "https://www.onlinenotarydirectory.com",
    loginUrl: "/login",
    registerUrl: "/register",
    searchUrl: "/search",
    features: ["login", "register", "search"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[placeholder*="search"], input[name="search"]' }
    }
  },

  chelleonwheels: {
    name: "Chelle on Wheels",
    baseUrl: "https://chelleonwheels.com",
    features: ["search", "profile"],
    selectors: {
      search: { input: 'input[type="search"], input[name="s"]' },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' }
    }
  },

  notaryrotary: {
    name: "Notary Rotary",
    baseUrl: "https://www.notaryrotary.com",
    loginUrl: "/login",
    registerUrl: "/register",
    searchUrl: "/search",
    features: ["login", "register", "search", "profile"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[placeholder*="search"], input[name="search"]' },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' }
    }
  },

  "123notary": {
    name: "123notary",
    baseUrl: "https://www.123notary.com",
    loginUrl: "/login.html",
    registerUrl: "/register.html",
    searchUrl: "/search.html",
    features: ["login", "register", "search", "profile"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[placeholder*="search"], input[name="search"], input[name="zip"]' },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' }
    }
  },

  snapdocs: {
    name: "Snapdocs",
    baseUrl: "https://www.snapdocs.com",
    loginUrl: "/login",
    registerUrl: "/register",
    searchUrl: "/notaries",
    features: ["login", "register", "search", "profile"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[placeholder*="search"], input[name="search"], input[name="zip"]' },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' }
    }
  },

  findanotary: {
    name: "Find a Notary",
    baseUrl: "https://www.findanotary.com",
    loginUrl: "/login.asp",
    registerUrl: "/register.asp",
    searchUrl: "/search.asp",
    features: ["login", "register", "search", "profile"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'input[type="submit"], button[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'input[type="submit"], button[type="submit"]' },
      search: { input: 'input[name="zip"], input[name="zipcode"], input[type="text"]' },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' }
    }
  },

  notarydepot: {
    name: "Notary Depot",
    baseUrl: "https://www.notarydepot.com",
    loginUrl: "/login",
    registerUrl: "/register",
    searchUrl: "/search",
    features: ["login", "register", "search"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[placeholder*="search"], input[name="search"]' }
    }
  },

  usnotaries: {
    name: "American Association of Notaries",
    baseUrl: "https://www.usnotaries.com",
    loginUrl: "/login",
    registerUrl: "/register",
    searchUrl: "/notary-search",
    features: ["login", "register", "search"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[placeholder*="search"], input[name="search"]' }
    }
  },

  notariescom: {
    name: "Notaries.com",
    baseUrl: "https://www.notaries.com",
    loginUrl: "/login",
    registerUrl: "/register",
    searchUrl: "/search",
    features: ["login", "register", "search", "profile"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Register")' },
      search: { input: 'input[type="search"], input[placeholder*="search"], input[name="search"]' },
      profile: { name: '[class*="name"], h1, h2', location: '[class*="location"], [class*="city"]', about: '[class*="about"], [class*="bio"]' }
    }
  },

  notarize: {
    name: "Notarize",
    baseUrl: "https://www.notarize.com",
    loginUrl: "/login",
    registerUrl: "/signup",
    features: ["login", "register"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Sign Up"), button:has-text("Register")' }
    }
  },

  onenotary: {
    name: "OneNotary",
    baseUrl: "https://onenotary.us",
    loginUrl: "/login",
    registerUrl: "/signup",
    features: ["login", "register"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Sign Up")' }
    }
  },

  bluenotary: {
    name: "BlueNotary",
    baseUrl: "https://bluenotary.us",
    loginUrl: "/login",
    registerUrl: "/signup",
    features: ["login", "register"],
    selectors: {
      login: { username: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], input[type="submit"]' },
      register: { firstName: 'input[name="first_name"], input[name="fname"]', lastName: 'input[name="last_name"], input[name="lname"]', email: 'input[name="email"], input[type="email"]', password: 'input[name="password"], input[type="password"]', submit: 'button[type="submit"], button:has-text("Sign Up")' }
    }
  }
};

function ensureDir(path) {
  const dir = path.split("/").slice(0, -1).join("/");
  if (dir && !existsSync(dir)) mkdirSync(dir, { recursive: true });
}

function randomDelay(ms) {
  return new Promise(r => setTimeout(r, ms + Math.random() * 1000));
}

function loadCookies(site) {
  const file = `${COOKIE_DIR}/${site}_cookies.json`;
  if (existsSync(file)) return JSON.parse(readFileSync(file, "utf-8"));
  return null;
}

function saveCookies(site, cookies) {
  const file = `${COOKIE_DIR}/${site}_cookies.json`;
  ensureDir(file);
  writeFileSync(file, JSON.stringify(cookies, null, 2));
}

async function findElement(page, selectors) {
  for (const sel of selectors) {
    const el = page.locator(sel).first();
    if (await el.count() > 0) return el;
  }
  return null;
}

async function doLogin(page, ctx, siteCfg, email, password) {
  const sel = siteCfg.selectors.login;
  const cookies = loadCookies(siteCfg.name.toLowerCase().replace(/\s+/g, ""));
  if (cookies) {
    try { await ctx.addCookies(cookies); } catch {}
    await page.goto(siteCfg.baseUrl, { timeout: 30000 });
    await page.waitForTimeout(3000);
    const url = page.url();
    if (!url.includes("login") && !url.includes("signin") && !url.includes("logon")) {
      return { success: true, method: "cookie", url };
    }
  }
  await page.goto(siteCfg.baseUrl + (siteCfg.loginUrl || "/login"), { timeout: 30000 });
  await page.waitForTimeout(2000);
  const uEl = await findElement(page, [sel.username]);
  if (uEl) await uEl.fill(email);
  const pEl = await findElement(page, [sel.password]);
  if (pEl) await pEl.fill(password);
  const sEl = await findElement(page, [sel.submit]);
  if (sEl) await sEl.click();
  await page.waitForTimeout(4000);
  const currentUrl = page.url();
  const loggedIn = !currentUrl.includes("login") && !currentUrl.includes("logon") && !currentUrl.includes("signin");
  if (loggedIn) {
    const slug = siteCfg.name.toLowerCase().replace(/\s+/g, "");
    saveCookies(slug, await ctx.cookies());
  }
  return { success: loggedIn, url: currentUrl };
}

async function doRegister(page, ctx, siteCfg, fields) {
  await page.goto(siteCfg.baseUrl + (siteCfg.registerUrl || "/register"), { timeout: 30000 });
  await page.waitForTimeout(2000);
  const sel = siteCfg.selectors.register;
  const fieldMap = {
    firstName: [sel.firstName],
    lastName: [sel.lastName],
    email: [sel.email],
    password: [sel.password],
    confirmPass: [sel.confirmPass],
    workPhone: [sel.workPhone],
    street: [sel.street],
    city: [sel.city],
    zip: [sel.zip]
  };
  for (const [key, value] of Object.entries(fields)) {
    if (!value) continue;
    const selectors = fieldMap[key];
    if (!selectors) continue;
    const el = await findElement(page, selectors.filter(Boolean));
    if (el) await el.fill(String(value));
  }
  const sEl = await findElement(page, [sel.submit]);
  if (sEl) {
    await sEl.click();
    await page.waitForTimeout(5000);
  }
  const currentUrl = page.url();
  const bodyText = await page.locator("body").innerText().catch(() => "");
  const hasError = bodyText.toLowerCase().includes("error") || bodyText.includes("required");
  return { success: currentUrl !== page.url() && !hasError, url: currentUrl };
}

async function doSearch(page, ctx, siteCfg, query) {
  const cookies = loadCookies(siteCfg.name.toLowerCase().replace(/\s+/g, ""));
  if (cookies) {
    try { await ctx.addCookies(cookies); } catch {}
  }
  await page.goto(siteCfg.baseUrl + (siteCfg.searchUrl || "/search"), { timeout: 30000 });
  await page.waitForTimeout(2000);
  const sel = siteCfg.selectors.search;
  const input = await findElement(page, [sel.input]);
  if (!input) return { error: "Search input not found", html: await page.locator("body").innerHTML().catch(() => "") };
  await input.fill(query);
  await input.press("Enter");
  await page.waitForTimeout(4000);

  // Extract emails from raw HTML
  const html = await page.locator("body").innerHTML().catch(() => "");
  const emailRe = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
  const rawEmails = [...new Set((html.match(emailRe) || []).map(e => e.toLowerCase()))];

  // Parse text-based results
  const body = await page.locator("body").innerText();
  const lines = body.split("\n").map(l => l.trim()).filter(Boolean);
  const results = [];
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].toLowerCase().includes("profile") || lines[i].toLowerCase().includes("view")) {
      const email = lines[i - 1] || "", phone = lines[i - 2] || "", name = lines[i - 3] || lines[i - 4] || "";
      if (name && name.length > 2 && !name.includes("results") && !name.includes("Search")) {
        results.push({ name, phone, email });
        if (results.length >= 20) break;
      }
    }
  }

  // Extract profile links
  const links = await page.locator("a").all();
  const profiles = [];
  for (const link of links) {
    const href = await link.getAttribute("href").catch(() => "");
    if (href && (href.includes("/profile") || href.includes("/notary") || href.includes("/view") || href.includes("/listing")) && !href.includes("login")) {
      const text = await link.innerText().catch(() => "");
      profiles.push({ text: text.substring(0, 80), href: href.startsWith("http") ? href : siteCfg.baseUrl + href });
      if (profiles.length >= 10) break;
    }
  }
  return { count: results.length, results, profiles, rawEmails };
}

async function doProfile(page, ctx, siteCfg, url) {
  const cookies = loadCookies(siteCfg.name.toLowerCase().replace(/\s+/g, ""));
  if (cookies) {
    try { await ctx.addCookies(cookies); } catch {}
  }
  const targetUrl = url.startsWith("http") ? url : siteCfg.baseUrl + url;
  await page.goto(targetUrl, { timeout: 30000 });
  await page.waitForTimeout(2000);
  const sel = siteCfg.selectors.profile || {};
  const name = await page.locator(sel.name || "h1, h2, [class*='name']").first().textContent().catch(() => "") || "";
  const location = await page.locator(sel.location || '[class*="location"], [class*="city"]').first().textContent().catch(() => "") || "";
  const about = await page.locator(sel.about || '[class*="about"], [class*="bio"], [class*="description"]').first().textContent().catch(() => "") || "";
  const email = await page.locator('[href*="mailto:"]').first().getAttribute("href").catch(() => "") || "";
  const phone = await page.locator('[href*="tel:"]').first().getAttribute("href").catch(() => "") || "";
  return { name: name.trim(), location: location.trim(), about: about.trim(), email: email.replace("mailto:", ""), phone: phone.replace("tel:", ""), url: page.url() };
}

async function doMessage(page, ctx, siteCfg, url, message) {
  const cookies = loadCookies(siteCfg.name.toLowerCase().replace(/\s+/g, ""));
  if (cookies) {
    try { await ctx.addCookies(cookies); } catch {}
  }
  const targetUrl = url.startsWith("http") ? url : siteCfg.baseUrl + url;
  await page.goto(targetUrl, { timeout: 30000 });
  await page.waitForTimeout(2000);
  const msgSel = siteCfg.selectors.message;
  if (msgSel) {
    const btn = await findElement(page, [msgSel.button]);
    if (btn && await btn.count() > 0) {
      await btn.click();
      await page.waitForTimeout(2000);
    }
    const ta = await findElement(page, [msgSel.textarea]);
    if (ta && await ta.count() > 0) {
      await ta.fill(message);
      await randomDelay(500);
      const send = await findElement(page, [msgSel.send]);
      if (send && await send.count() > 0) {
        await send.click();
        await page.waitForTimeout(2000);
        return { success: true };
      }
      return { success: false, error: "Send button not found" };
    }
    return { success: false, error: "Message textarea not found" };
  }
  const genericTextarea = page.locator("textarea, [contenteditable='true'], [role='textbox']").first();
  if (await genericTextarea.count() > 0) {
    await genericTextarea.fill(message);
    const sendBtn = page.locator('button[type="submit"], button:has-text("Send"), button:has-text("Message")').first();
    if (await sendBtn.count() > 0) {
      await sendBtn.click();
      await page.waitForTimeout(2000);
      return { success: true };
    }
  }
  return { success: false, error: "Message form not found" };
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function loadJSON(file, fallback) {
  if (!existsSync(file)) return fallback;
  try { return JSON.parse(readFileSync(file, "utf8")); } catch { return fallback; }
}

function saveJSON(file, data) {
  const d = file.split("/").slice(0, -1).join("/");
  if (d && !existsSync(d)) mkdirSync(d, { recursive: true });
  writeFileSync(file, JSON.stringify(data, null, 2));
}

function loadTemplates() {
  if (!existsSync(TEMPLATES_FILE)) return {};
  try { return JSON.parse(readFileSync(TEMPLATES_FILE, "utf-8")); } catch { return {}; }
}

function getSiteTemplates(siteKey) {
  const all = loadTemplates();
  return all[siteKey] || null;
}

function listSites() {
  const result = {};
  for (const [key, val] of Object.entries(SITES)) {
    result[key] = { name: val.name, baseUrl: val.baseUrl, features: val.features, site_type: null };
    const tmpl = getSiteTemplates(key);
    if (tmpl) result[key].site_type = tmpl.site_type;
  }
  return result;
}

async function main() {
  const siteKey = process.argv[2]?.toLowerCase().replace(/[^a-z0-9]/g, "");
  const action = process.argv[3];

  if (!siteKey || siteKey === "list") {
    console.log(JSON.stringify({ sites: listSites() }));
    return;
  }

  if (!action) {
    console.log(JSON.stringify({ error: "Usage: node notary_sites.mjs <site> <action> [args...]", sites: Object.keys(SITES) }));
    return;
  }

  if (action === "list-templates") {
    const tmpl = getSiteTemplates(siteKey);
    if (!tmpl) {
      console.log(JSON.stringify({ error: `No templates defined for site: ${siteKey}` }));
      return;
    }
    const list = (tmpl.message_templates || []).map((t, i) => ({ index: i, subject: t.subject }));
    console.log(JSON.stringify({ site: siteKey, site_type: tmpl.site_type, description: tmpl.description, templates: list }));
    return;
  }

  // "all" site key runs collect-zips on every site with "search" feature
  if (siteKey === "all" && action === "collect-zips") {
    const zipCount = parseInt(process.argv[4]) || 50;
    const siteKeys = Object.keys(SITES).filter(k => SITES[k].features.includes("search"));
    const allContacts = loadJSON(CONTACTS_FILE, []);
    const seenEmails = new Set(allContacts.map(c => c.email));
    let totalFound = 0;

    console.log(JSON.stringify({ step: "collect-zips-all", sites: siteKeys, zipsPerSite: zipCount, existing: seenEmails.size }));

    const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await ctx.newPage();

    for (const sk of siteKeys) {
      const cfg = SITES[sk];
      if (!cfg.features.includes("search")) continue;
      console.log(JSON.stringify({ step: "collect-zips-all", site: sk, name: cfg.name }));

      const shuffled = [...CA_ZIPS].sort(() => Math.random() - 0.5).slice(0, Math.min(zipCount, CA_ZIPS.length));
      let siteFound = 0;

      for (let i = 0; i < shuffled.length; i++) {
        const zip = shuffled[i];
        try {
          const searchRes = await doSearch(page, ctx, cfg, zip);
          if (searchRes.profiles && searchRes.profiles.length > 0) {
            for (const profile of searchRes.profiles.slice(0, 5)) {
              const profUrl = profile.href;
              if (!profUrl) continue;
              try {
                const profData = await doProfile(page, ctx, cfg, profUrl);
                const email = (profData.email || "").toLowerCase().trim();
                if (email && !seenEmails.has(email) && email.includes("@") && !email.includes("example")) {
                  allContacts.push({
                    email,
                    name: profData.name || profile.text || "",
                    phone: profData.phone || "",
                    location: profData.location || "",
                    source: sk,
                    zip,
                    scraped_at: new Date().toISOString()
                  });
                  seenEmails.add(email);
                  totalFound++;
                  siteFound++;
                }
              } catch (e) {}
              await sleep(1000 + Math.random() * 1000);
            }
          }
        } catch (e) {}
        await sleep(2000 + Math.random() * 2000);
      }

      saveJSON(CONTACTS_FILE, allContacts);
      console.log(JSON.stringify({ step: "collect-zips-all", site: sk, found: siteFound, total: allContacts.length }));
    }

    await browser.close();
    console.log(JSON.stringify({ step: "collect-zips-all", status: "complete", sites: siteKeys.length, found: totalFound, total: allContacts.length }));
    return;
  }

  const siteCfg = SITES[siteKey];
  if (!siteCfg) {
    console.log(JSON.stringify({ error: `Unknown site: ${siteKey}. Available: ${Object.keys(SITES).join(", ")}` }));
    return;
  }

  if (!siteCfg.features.includes(action) && action !== "collect-zips") {
    console.log(JSON.stringify({ error: `Site '${siteKey}' does not support '${action}'. Supports: ${siteCfg.features.join(", ")}` }));
    return;
  }

  const args = process.argv.slice(4);
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  let result;

  try {
    switch (action) {
      case "login": {
        const [email, pass] = [args[0], args[1]];
        if (!email || !pass) { result = { error: "Email and password required" }; break; }
        result = await doLogin(page, ctx, siteCfg, email, pass);
        break;
      }
      case "register": {
        const fields = { firstName: args[0], lastName: args[1], email: args[2], password: args[3], confirmPass: args[4] || args[3], workPhone: args[5], street: args[6], city: args[7], zip: args[8] };
        result = await doRegister(page, ctx, siteCfg, fields);
        break;
      }
      case "search": {
        const query = args.join(" ");
        if (!query) { result = { error: "Search query required" }; break; }
        result = await doSearch(page, ctx, siteCfg, query);
        break;
      }
      case "profile": {
        const url = args[0];
        if (!url) { result = { error: "Profile URL required" }; break; }
        result = await doProfile(page, ctx, siteCfg, url);
        break;
      }
      case "message": {
        const [url, ...msgParts] = args;
        const msg = msgParts.join(" ");
        if (!url) { result = { error: "URL and message required" }; break; }
        const templateMatch = msg.match(/^--template=(\d+)/);
        let finalMsg = msg;
        if (templateMatch) {
          const idx = parseInt(templateMatch[1]);
          const tmpl = getSiteTemplates(siteKey);
          const templates = tmpl?.message_templates;
          if (!templates || !templates[idx]) { result = { error: `Template index ${idx} not found for ${siteKey}. Use 'list-templates' to see available.` }; break; }
          finalMsg = `${templates[idx].subject}\n\n${templates[idx].body}`;
        }
        result = await doMessage(page, ctx, siteCfg, url, finalMsg);
        break;
      }
      case "collect-zips": {
        const zipCount = parseInt(args[0]) || 50;
        const shuffled = [...CA_ZIPS].sort(() => Math.random() - 0.5).slice(0, Math.min(zipCount, CA_ZIPS.length));
        const allContacts = loadJSON(CONTACTS_FILE, []);
        const seenEmails = new Set(allContacts.map(c => c.email));
        let totalFound = 0;

        console.log(JSON.stringify({ step: "collect-zips", site: siteKey, zips: shuffled.length, existing: seenEmails.size }));

        for (let i = 0; i < shuffled.length; i++) {
          const zip = shuffled[i];
          try {
            const searchRes = await doSearch(page, ctx, siteCfg, zip);
            // Collect emails from raw search results page
            if (searchRes.rawEmails) {
              for (const email of searchRes.rawEmails) {
                if (!seenEmails.has(email) && email.includes("@") && !email.includes("example")) {
                  allContacts.push({
                    email,
                    name: "",
                    phone: "",
                    location: "",
                    source: siteKey,
                    zip,
                    scraped_at: new Date().toISOString()
                  });
                  seenEmails.add(email);
                  totalFound++;
                }
              }
            }
            // Also check results table for emails mis-filed as phone
            if (searchRes.results) {
              for (const r of searchRes.results) {
                const possibleEmails = [r.email, r.phone].filter(e => e && e.includes("@") && !seenEmails.has(e.toLowerCase()));
                for (const email of possibleEmails) {
                  allContacts.push({
                    email: email.toLowerCase(),
                    name: r.name || "",
                    phone: r.phone && !r.phone.includes("@") ? r.phone : "",
                    location: "",
                    source: siteKey,
                    zip,
                    scraped_at: new Date().toISOString()
                  });
                  seenEmails.add(email.toLowerCase());
                  totalFound++;
                }
              }
            }
            // Visit profile pages for more emails
            if (searchRes.profiles && searchRes.profiles.length > 0) {
              for (const profile of searchRes.profiles.slice(0, 5)) {
                const profUrl = profile.href;
                if (!profUrl) continue;
                try {
                  const profData = await doProfile(page, ctx, siteCfg, profUrl);
                  const email = (profData.email || "").toLowerCase().trim();
                  if (email && !seenEmails.has(email) && email.includes("@") && !email.includes("example")) {
                    allContacts.push({
                      email,
                      name: profData.name || profile.text || "",
                      phone: profData.phone || "",
                      location: profData.location || "",
                      source: siteKey,
                      zip,
                      scraped_at: new Date().toISOString()
                    });
                    seenEmails.add(email);
                    totalFound++;
                  }
                } catch (e) {}
                await sleep(1000 + Math.random() * 1000);
              }
            }
          } catch (e) {}

          if ((i + 1) % 10 === 0) {
            saveJSON(CONTACTS_FILE, allContacts);
            console.log(JSON.stringify({ step: "collect-zips", progress: `${i + 1}/${shuffled.length}`, found: totalFound, total: allContacts.length }));
          }
          await sleep(2000 + Math.random() * 2000);
        }

        saveJSON(CONTACTS_FILE, allContacts);
        result = { step: "collect-zips", status: "complete", site: siteKey, zipsScraped: shuffled.length, found: totalFound, total: allContacts.length };
        break;
      }
      default:
        result = { error: `Unknown action: ${action}` };
    }
  } catch (e) { result = { error: e.message }; }
  finally {
    await browser.close();
    console.log(JSON.stringify(result));
  }
}

main();

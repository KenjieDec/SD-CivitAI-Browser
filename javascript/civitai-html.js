"use strict";
let scrolling = false;
let isTransitioning = false;
let copyClickable = true;
let dataClickable = true;
function select_model(model_name) {
	if(scrolling) return
	console.log(model_name)
	let model_dropdown = gradioApp().querySelector('#selected_model textarea');
	if (model_dropdown && model_name) {
		model_dropdown.value = model_name;
		updateInput(model_dropdown)
	}
}

function nextSlide(btn, datas) {

	if (isTransitioning) return; 
	isTransitioning = true;
  
	var container = btn.parentNode;
	var prevBtn = container.querySelector(".prev-btn");
	var slider = container.querySelector('.images');
	var currentSlide = slider.querySelector('.active');
	var nextSlide = currentSlide.nextElementSibling;
  
	if (!nextSlide) {
	  nextSlide = slider.firstElementChild;
	}
  
	currentSlide.style.animation = 'slideOutRight 0.7s forwards';
	nextSlide.style.animation = 'slideInRight 0.7s forwards';
  
	nextSlide.classList.add('active');
	nextSlide.style.visibility = 'visible';
  
	const currentAspectRatioDecimal = (currentSlide.width / currentSlide.height).toFixed(2)
	const nextAspectRatioDecimal = (nextSlide.width / nextSlide.height).toFixed(2)
    
    changeButtonTop(prevBtn, btn, nextAspectRatioDecimal)
    
    prevBtn.style.animation = "slideOutButtonRight 0.4s forwards";
    btn.style.animation = "slideOutButtonRight 0.4s forwards";
  
	const containerRect = slider.getBoundingClientRect();
	const element1Y = nextSlide.getBoundingClientRect().top - containerRect.top;
	const element2Y = currentSlide.getBoundingClientRect().top - containerRect.top;

	if(element1Y > element2Y) {
		nextSlide.style.marginTop = `-${currentSlide.height+2}px`; 
	} else {
		currentSlide.style.marginTop = `-${currentSlide.height+2}px`; 
	}
  
    var animationChange = function () {
      btn.removeEventListener('animationend', animationChange);
		
      prevBtn.style.animation = "slideInButtonRight 0.3s forwards";
      btn.style.animation = "slideInButtonRight 0.3s forwards";	
    }
  	btn.addEventListener('animationend', animationChange);
    
	var currentSlideHandler = function () {
	  currentSlide.classList.remove('active');
	  currentSlide.removeEventListener('animationend', currentSlideHandler);
	  currentSlide.style.visibility = 'hidden';
      currentSlide.style.marginTop = `20px`; 
	  nextSlide.style.marginTop = `20px`;
	  isTransitioning = false;
	};
  
	currentSlide.addEventListener('animationend', currentSlideHandler);

	// Get the image link and update the text based on it
	var imageLink = nextSlide.getAttribute('src');
	processTexts(imageLink, btn, datas);
}
  
function prevSlide(btn, datas) {
	if (isTransitioning) return; 
	isTransitioning = true;
	
	var container = btn.parentNode;
	var nxtBtn = container.querySelector(".next-btn");
	var slider = container.querySelector('.images');
	var currentSlide = slider.querySelector('.active');
	var prevSlide = currentSlide.previousElementSibling;
  
	if (!prevSlide) {
	  prevSlide = slider.lastElementChild;
	}
  
	
	prevSlide.classList.add('active');
	prevSlide.style.visibility = 'visible';
    
    const currentAspectRatioDecimal = (currentSlide.width / currentSlide.height).toFixed(2)
    const prevAspectRatioDecimal = (prevSlide.width / prevSlide.height).toFixed(2)
    
	currentSlide.style.animation = 'slideOutLeft 0.7s forwards';
	prevSlide.style.animation = 'slideInLeft 0.7s forwards';
    
    changeButtonTop(btn, nxtBtn, prevAspectRatioDecimal)
    
    nxtBtn.style.animation = "slideOutButtonLeft 0.4s forwards";
    btn.style.animation = "slideOutButtonLeft 0.4s forwards";
    
	const containerRect = slider.getBoundingClientRect();
	const element1Y = prevSlide.getBoundingClientRect().top - containerRect.top;
	const element2Y = currentSlide.getBoundingClientRect().top - containerRect.top;
	
	if(element1Y < element2Y) {
	  currentSlide.style.marginTop = `-${currentSlide.height+2}px`; 
	} else {
	  prevSlide.style.marginTop = `-${currentSlide.height+2}px`; 
	}
    

    var animationChange = function () {
      btn.removeEventListener('animationend', animationChange);
		
      nxtBtn.style.animation = "slideInButtonLeft 0.3s forwards";
      btn.style.animation = "slideInButtonLeft 0.3s forwards";	
    }
  	btn.addEventListener('animationend', animationChange);
	
	var currentSlideHandler = function () {
	  currentSlide.classList.remove('active');
	  currentSlide.removeEventListener('animationend', currentSlideHandler);
	  currentSlide.style.visibility = 'hidden';
      currentSlide.style.marginTop = `20px`; 
	  prevSlide.style.marginTop = `20px`;
      isTransitioning = false;
	};
  
	currentSlide.addEventListener('animationend', currentSlideHandler);
	
	// Get the image link and update the text based on it
	var imageLink = prevSlide.getAttribute('src');
	processTexts(imageLink, btn, datas);
}

function processTexts(imageLink, btn, datas) {
	var pythonData = datas
	const prompts = pythonData[imageLink]["prompts"]
	const neg_prompts = pythonData[imageLink]["neg_prompts"]
	const steps = pythonData[imageLink]["steps"]
	const seed = pythonData[imageLink]["seed"]
	const sampler = pythonData[imageLink]["sampler"]
	const cfg_scale = pythonData[imageLink]["cfg_scale"]
	const clip_skip = pythonData[imageLink]["clip_skip"]
	updateHtml(prompts, neg_prompts, steps, seed, sampler, cfg_scale, clip_skip, btn)

}

function updateHtml(prompts, neg_prompts, steps, seed, sampler, cfg_scale, clip_skip, btn){
	var buttonContainer = btn.parentNode.parentNode.parentNode;
	const baseDiv = buttonContainer.querySelector('.inside-pc');
	const promptCodeBlock = buttonContainer.querySelector('.prompt-container .code-block');
	const negativePromptCodeBlock = buttonContainer.querySelector('.prompt-container .stack-container:nth-child(2) .code-block');
	const stepsCode = buttonContainer.querySelector('.grid-container .group-container:nth-child(2) .code-text');
	const seedCode = buttonContainer.querySelector('.grid-container .group-container:nth-child(3) .code-text');
	const samplerCode = buttonContainer.querySelector('.group-container:nth-child(3) .code-text');
	const cfgCode = buttonContainer.querySelector('.grid-container .group-container:nth-child(1) .code-text');
	const clipCode = buttonContainer.querySelector('.grid-container .group-container:nth-child(4) .code-text');
	
	
	baseDiv.style.animation = 'slideOutLowRight 0.1s forwards';
	
	var baseDivHandler = function () {
        promptCodeBlock.innerText = prompts
        negativePromptCodeBlock.innerText = neg_prompts
        stepsCode.innerText = steps
        seedCode.innerText = seed
        samplerCode.innerText = sampler
        cfgCode.innerText = cfg_scale
        clipCode.innerText = clip_skip
		baseDiv.style.animation = 'slideInLowLeft 0.4s forwards';
	};
	baseDiv.addEventListener('animationend', baseDivHandler);
	
}

function copyTextToClipboard(text) {
	const textarea = document.createElement('textarea');
	textarea.value = text;
	document.body.appendChild(textarea);
	textarea.select();
	document.execCommand('copy');
	document.body.removeChild(textarea);
}

function handleCopyButtonClick(btn) {
	if(copyClickable) return;
	copyClickable = false;
	const codeBlock = btn.closest('.stack-container').querySelector('.code-block');
	const code = codeBlock.innerText;
	copyTextToClipboard(code);
	const buttonLabel = btn.closest('.stack-container').querySelector('.copy-button');

	buttonLabel.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="checked-svg"><path d="M5 12l5 5l10 -10"></path></svg>';

	setTimeout(() => {
		buttonLabel.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="copy-svg">
			<path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z"></path>
			<path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2"></path>
		</svg>`;
		copyClickable = true;
	}, 3000); // Change back to normal after 3 seconds (adjust the duration as needed)
}

function handleCopyDataButtonClick(btn) {
	if(dataClickable) return;
	dataClickable = false;
    
	const buttonLabel = btn.querySelector('.button-label');
	const buttonContainer = btn.parentElement;
	const buttonParent = btn
	
	// Code to copy data goes here
	const promptCodeBlock = buttonContainer.querySelector('.prompt-container .code-block');
	const negativePromptCodeBlock = buttonContainer.querySelector('.prompt-container .stack-container:nth-child(2) .code-block');
	const stepsCode = buttonContainer.querySelector('.grid-container .group-container:nth-child(2) .code-text').innerText;
	const seedCode = buttonContainer.querySelector('.grid-container .group-container:nth-child(3) .code-text').innerText;
	const samplerCode = buttonContainer.querySelector('.group-container:nth-child(3) .code-text').innerText;
	const cfgCode = buttonContainer.querySelector('.grid-container .group-container:nth-child(1) .code-text').innerText;
	const clipCode = buttonContainer.querySelector('.grid-container .group-container:nth-child(4) .code-text').innerText;

	const copiedData = `Prompt: ${promptCodeBlock.innerText}\nNegative prompt: ${negativePromptCodeBlock.innerText}\nSteps: ${stepsCode}, Seed: ${seedCode}, Sampler: ${samplerCode}, CFG scale: ${cfgCode}, Clip skip: ${clipCode}`;
	copyTextToClipboard(copiedData);

	buttonLabel.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="data-checked-svg"><path d="M5 12l5 5l10 -10"></path></svg> Copied';
	buttonLabel.removeAttribute("style", "color: rgb(150, 242, 215) !important;")
	buttonParent.setAttribute("style", "background-color: rgba(9, 146, 104, 0.2)")

	setTimeout(() => {
	  buttonLabel.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="data-copy-svg"> <path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z"></path> <path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2"></path> </svg> Copy Generation Data';
	  buttonLabel.removeAttribute("style", "color: rgb(150, 242, 215) !important;")
	  buttonParent.setAttribute("style", "background-color: rgba(9, 146, 104, 0.2)")
	  dataClickable = true;
	}, 3000); // Change back to normal after 3 seconds (adjust the duration as needed)
}

function changeButtonTop(prevButton, nextButton, aspectRatio){
	if (aspectRatio >= 0.6) {
		// For aspect ratios greater than or equal to 0.6
		if (aspectRatio >= 1.6) {
		  nextButton.style.top = prevButton.style.top = "84%";
		} else if (aspectRatio >= 1.1) {
		  nextButton.style.top = prevButton.style.top = "88%";
		} else if (aspectRatio >= 0.8) {
		  nextButton.style.top = prevButton.style.top = "89%";
		} else {
		  // Default value for aspect ratios greater than or equal to 0.6
		  nextButton.style.top = prevButton.style.top = "90%";
		}
	  } else {
		// For aspect ratios less than 0.6
		nextButton.style.top = prevButton.style.top = "92%";
	}
}
function roundToNearest5(value) {
	return Math.round(value / 5) * 5;
}

function calculateValue(input) {
	const m = 85 / 9.1; 
	const c = 100 - m * 21;
	return roundToNearest5(m * input + c);
}

function calculateMaxWidthValue(input) {
    // Pattern: Output = m * input + c
    const m = 1200 / 10; 
    const c = 1762 - m * 20;
    return Math.max((m * input + c) - ( 5.5 * 114 ), 0);
}

// Function to handle the mutation
async function handleMutation(mutationsList, observer) {
	for (let mutation of mutationsList) {
	  if (mutation.type === 'childList' && mutation.target.querySelector('.civmodellist')) {
		console.log('The <div class="column civmodellist"> has appeared or changed.');
		const images = mutation.target.querySelectorAll('.civmodelcard');
		
		images.forEach(civcard => {
			const image = civcard.querySelector('img');
			image.setAttribute('draggable', 'false');
		});
		
		const track = mutation.target.querySelector(".civmodellist")
		let trackPosition = 0;
		let scrollSpeed = 1.5;
	
		const handleOnDown = e => {
			track.dataset.mouseDownAt = e.clientX;
			track.dataset.prevPercentage = trackPosition;
	  	};
	
		const handleOnUp = () => {
			track.dataset.mouseDownAt = "0";  
			track.dataset.prevPercentage = "0";
			scrolling = false;
		}
	
		const handleOnMove = e => {
			
			/*const mouseDelta = parseFloat(track.dataset.mouseDownAt) - e.clientX,
					maxDelta = window.innerWidth / scrollSpeed;
				
			var calculatedValue = await calculateValue(images.length);
				if(calculatedValue < 0) calculatedValue = 0;
			var percentage = (mouseDelta / maxDelta) * -calculatedValue,
					nextPercentageUnconstrained = parseFloat(track.dataset.prevPercentage) + percentage,
					nextPercentage = Math.max(Math.min(nextPercentageUnconstrained, 0), -calculatedValue);
		
			if(!nextPercentage || nextPercentage == undefined || nextPercentage == NaN) nextPercentage = 0;
			track.dataset.percentage = nextPercentage;
		
			track.animate({
				transform: `translate(${nextPercentage}%)`
			}, { duration: 1200, fill: "forwards" });
			*/
			if(track.dataset.mouseDownAt === "0") return;
			scrolling = true;
			
			const mouseDelta = parseFloat(track.dataset.mouseDownAt) - e.clientX;
			trackPosition = Math.min(Math.max(parseFloat(track.dataset.prevPercentage) + mouseDelta * scrollSpeed, 0), calculateMaxWidthValue(images.length));
		
			track.animate({
				transform: `translateX(${trackPosition * -1}px)`
			}, { duration:  2000, fill: "forwards" });
	
		}
	
		/* -- Had to add extra lines for touch events -- */
	
		window.onmousedown = e => handleOnDown(e);
	
		window.ontouchstart = e => handleOnDown(e.touches[0]);
	
		window.onmouseup = e => handleOnUp(e);
	
		window.ontouchend = e => handleOnUp(e.touches[0]);
	
		window.onmousemove = e => handleOnMove(e);
	
		window.ontouchmove = e => handleOnMove(e.touches[0]);
	  }
	  if (mutation.type === 'childList' && mutation.target.querySelector('.active')) {
		console.log('The <div class="active"> has appeared or changed.');
		const currentSlide = mutation.target.querySelector(".active");
		const prevBtn = currentSlide.parentNode.parentNode.querySelector(".prev-btn");
		const nxtBtn = currentSlide.parentNode.parentNode.querySelector(".next-btn");
		const prevAspectRatioDecimal = (currentSlide.width / currentSlide.height).toFixed(2)
		
		await changeButtonTop(prevBtn, nxtBtn, prevAspectRatioDecimal)
	
		setTimeout(() => {
			prevBtn.style.animation = "slideInButtonRight 0.5s forwards";
			nxtBtn.style.animation = "slideInButtonRight 0.5s forwards";
		  }, 235);
	  }
	}
}

// Select the target node that you want to observe
const targetNode = document; // You can change this to a specific container if you want to limit the observation to a particular area.

// Options for the observer (specify what types of mutations to observe)
const observerOptions = {
	childList: true, // Observe direct children being added or removed
	subtree: true, // Observe all descendants, not just direct children
};

// Create a new observer
const observer = new MutationObserver(handleMutation);

// Start observing the target node for mutations
observer.observe(targetNode, observerOptions);